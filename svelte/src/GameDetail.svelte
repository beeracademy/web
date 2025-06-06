<script module lang="ts">
import { formatDate, formatDuration, is_staff, moment } from "./globals";
import type { ChugData, GameData, GamePlayerData } from "./types";
</script>

<script lang="ts">
	import { onMount } from "svelte";

	import Map from "./Map.svelte";
	import Image from "./Image.svelte";
	import Players from "./Players.svelte";
	import CardCell from "./CardCell.svelte";
	import Chug from "./Chug.svelte";
	import SipsGraph from "./SipsGraph.svelte";
	import TimeGraph from "./TimeGraph.svelte";

	let game_data = $state(JSON.parse(
		document.getElementById("game_data")!.textContent!
	) as GameData);
	const ordered_gameplayers = JSON.parse(
		document.getElementById("ordered_gameplayers")!.textContent!
	) as GamePlayerData[];

	async function updateData() {
		if (game_data.end_datetime || game_data.dnf) return;

		try {
			const res = await fetch(`/api/games/${game_data.id}/`);
			game_data = await res.json();
		} catch (e) {}

		setTimeout(updateData, 1000);
	}

	updateData();

	let { duration, durationSinceLastActivity } = $derived.by(() => {
		let end_datetime: Date;
		let lastActivityStartDeltaMs = null;
		if (game_data.end_datetime) {
			end_datetime = new Date(game_data.end_datetime);
		} else {
			if (game_data.dnf) {
				const start_date = new Date(game_data.start_datetime!);
				if (game_data.cards.length === 0) {
					end_datetime = start_date;
				} else {
					end_datetime = new Date(
						start_date.getTime() +
							game_data.cards[game_data.cards.length - 1].start_delta_ms
					);
				}
			} else {
				end_datetime = new Date();
				if (game_data.cards.length === 0) {
					lastActivityStartDeltaMs = 0;
				} else {
					const lastCard = game_data.cards[game_data.cards.length - 1];
					if (lastCard.chug_duration_ms) {
						lastActivityStartDeltaMs =
							lastCard.chug_start_start_delta_ms! + lastCard.chug_duration_ms;
					} else if (lastCard.chug_start_start_delta_ms) {
						lastActivityStartDeltaMs = lastCard.chug_start_start_delta_ms;
					} else {
						lastActivityStartDeltaMs = lastCard.start_delta_ms;
					}
				}
			}
		}
		let duration = null;
		let durationSinceLastActivity = null;
		if (game_data.start_datetime) {
			const start_datetime = new Date(game_data.start_datetime);
			duration = end_datetime.getTime() - start_datetime.getTime();
			if (lastActivityStartDeltaMs !== null) {
				durationSinceLastActivity =
					Date.now() - start_datetime.getTime() - lastActivityStartDeltaMs;
			}
		}
		return { duration, durationSinceLastActivity };
	});

	let chugs: ChugData[] = $derived.by(() => {
		const chugs = [];
		for (let i = 0; i < game_data.cards.length; i++) {
			const card = game_data.cards[i];
			if (card.value === 14) {
				const gameplayer = ordered_gameplayers[i % ordered_gameplayers.length];
				chugs.push({
					card: card,
					gameplayer: gameplayer,
				});
			}
		}
		return chugs;
	});

	let chat_messages: HTMLDivElement = $state(), chat_input: HTMLInputElement = $state();
	let toastContainer: HTMLDivElement = $state();
	onMount(function () {
		const scheme = window.location.protocol === "https:" ? "wss" : "ws";
		let socket: WebSocket | null = null;
		let myChatId: string | null = null;

		startSocket();

		function startSocket() {
			socket = new WebSocket(
				scheme + "://" + window.location.host + "/ws/chat/" + game_data.id + "/"
			);

			socket.addEventListener("open", function (e) {
				chat_input.disabled = false;
			});

			socket.addEventListener("close", function () {
				console.error("Chat socket closed unexpectedly!");
				disconnected();
			});

			socket.addEventListener("error", function () {
				console.error("Got an error from the chat socket!");
				socket!.close();
			});

			socket.addEventListener("message", function (e) {
				var data = JSON.parse(e.data);

				if (data.event === "chat_id") {
					myChatId = data.chat_id;
					return;
				}

				var username = data["username"];
				if (data.is_game) {
					username = "Game";
				} else if (!username) {
					username = "Guest";
				}

				let chatId = data.chat_id;

				var userUrl: string;
				if (data.user_id) {
					userUrl = `/players/${data.user_id}`;
				} else if (data.is_game) {
					userUrl = window.location.href;
				} else {
					userUrl = "#";
				}

				var message = null;
				var isInfo = false;
				switch (data["event"]) {
					case "message":
						message = data["message"];
						break;
					case "connect":
						message = "connected";
						isInfo = true;
						break;
					case "disconnect":
						message = "disconnected";
						isInfo = true;
						break;
				}

				if (message) {
					var d = new Date(data["datetime"]);
					var time = moment(d).format("HH:mm:ss");

					addMessage(username, userUrl, message, isInfo, time, chatId);
				} else {
					console.error("Unknown message received:");
					console.error(data);
				}
			});
		}

		chat_input.addEventListener("keyup", function (e) {
			if (e.keyCode === 13) {
				socket!.send(
					JSON.stringify({
						message: chat_input.value,
					})
				);

				chat_input.value = "";
			}
		});

		function disconnected() {
			chat_input.disabled = true;
			setTimeout(startSocket, 1000);
		}

		function addMessage(
			user: string,
			userUrl: string,
			msg: string,
			isInfo: boolean,
			_time: string,
			chatId: string
		) {
			let elm = document.createElement("div");
			elm.classList.add("message");

			if (isInfo) {
				elm.classList.add("info-message");
			}

			var userElm = document.createElement("a");
			userElm.href = userUrl;
			userElm.target = "_blank";
			userElm.innerText = user;
			if (!isInfo) {
				userElm.innerText += ":";
			}
			elm.appendChild(userElm);

			elm.appendChild(document.createTextNode(" "));

			var textElm = document.createTextNode(msg);
			elm.appendChild(textElm);

			chat_messages.appendChild(elm);

			chat_messages.scrollTo(0, chat_messages.scrollHeight);

			if (!isInfo && chatId !== myChatId) {
				const toastHeader = document.createElement("div");
				toastHeader.classList.add("toast-header");
				toastHeader.textContent = user;

				const toastBody = document.createElement("div");
				toastBody.classList.add("toast-body");
				toastBody.textContent = msg;

				const toastElm = document.createElement("div");
				toastElm.appendChild(toastHeader);
				toastElm.appendChild(toastBody);

				toastContainer.appendChild(toastElm);

				(window as any)
					.jQuery(toastElm)
					.toast({ delay: 2000 })
					.on("hidden.bs.toast", function () {
						toastContainer.removeChild(this);
					})
					.toast("show");
			}
		}
	});

	onMount(() => {
		const footer = document.querySelector("footer");
		const game = document.querySelector(".game");
		const gameWrapper = document.querySelector(".game-wrapper");

		function handleResize() {
			const parent = window.innerWidth <= 1024 ? gameWrapper : game;
			parent.appendChild(footer);
		}

		window.addEventListener("resize", handleResize);

		handleResize();
	});
</script>

<div class="game-wrapper">
	<h2 class="players-header">Players</h2>
	<div class="players">
		<Players {game_data} {ordered_gameplayers} />
	</div>
	<div class="game">
		<div class="container">
			<h2>
				Meta
				{#if is_staff}
					<a
						class="btn btn-primary float-right text-light col-md-auto"
						href="/admin/games/game/{game_data.id}/change/">Edit</a
					>
					<br /><br class="d-lg-none" />
				{/if}
			</h2>

			<hr />

			<p class="description">{@html game_data.description_html}</p>

			<table class="table">
				<thead>
					<tr>
						<th scope="col">Game id</th>
						<th scope="col">Start Time</th>
						<th scope="col">End Time</th>
						<th scope="col">Duration</th>
						{#if durationSinceLastActivity !== null}
							<th scope="col">Time since last activity</th>
						{/if}
					</tr>
				</thead>
				<tbody>
					<tr>
						<td>{game_data.id}</td>
						<td id="game_start_datetime">
							{#if game_data.start_datetime}
								{formatDate(new Date(game_data.start_datetime))}
							{:else}
								?
							{/if}
						</td>
						<td id="game_end_datetime">
							{#if game_data.dnf}
								DNF
							{:else if game_data.end_datetime}
								{formatDate(new Date(game_data.end_datetime))}
							{:else}
								-
							{/if}
						</td>
						<td id="game_duration">
							{#if duration}
								{formatDuration(duration)}
							{:else}
								?
							{/if}
						</td>
						{#if durationSinceLastActivity !== null}
							<td>
								{formatDuration(durationSinceLastActivity)}
							</td>
						{/if}
					</tr>
				</tbody>
			</table>

			{#if game_data.location.latitude !== null}
				<h2>Location</h2>
				<hr />
				<Map location={game_data.location} />
			{/if}

			{#if game_data.image !== null}
				<h2>Image</h2>
				<hr />
				<Image url={game_data.image} />
			{/if}

			<h2>Chugs</h2>

			<hr />

			<div class="container">
				<div id="chugs_container" class="row justify-content-md-center">
					{#each chugs as chug}
						{#if game_data.start_datetime}
							<Chug start_datetime={game_data.start_datetime} {chug} game_dnf={game_data.dnf} />
						{/if}
					{/each}
				</div>
			</div>

			<h2>Round overview</h2>

			<hr />

			<table
				id="cards_table"
				class="table table-bordered table-striped table-hover table-sm"
			>
				<thead>
					<tr>
						<th scope="col">Round</th>
						{#each ordered_gameplayers as gp}
							<th scope="col">{gp.user.username}</th>
						{/each}
					</tr>
				</thead>
				<tbody>
					{#each Array(13) as _, i}
						<tr>
							<td>{i + 1}</td>
							{#each ordered_gameplayers as _, j}
								<CardCell
									card={game_data.cards[i * ordered_gameplayers.length + j]}
								/>
							{/each}
						</tr>
					{/each}
				</tbody>
			</table>

			<h2>Graphs</h2>

			<hr />

			<br />
			<br />
			<SipsGraph {game_data} {ordered_gameplayers} />
			<br />
			<br />
			<br />
			<TimeGraph {game_data} {ordered_gameplayers} />
		</div>
	</div>

	<div class="chat">
		<div class="info">Chat</div>
		<div class="messages" id="chat-messages" bind:this={chat_messages}></div>
		<input
			id="chat-input"
			autocomplete="off"
			type="text"
			disabled
			placeholder="Send a message"
			bind:this={chat_input}
		/>
	</div>
</div>

<div
	aria-live="polite"
	aria-atomic="true"
	class="d-flex justify-content-center align-items-center"
>
	<div
		style="position: absolute; top: 100px; right: 100px; z-index: 10000; min-height: 200px;"
		bind:this={toastContainer}
></div>
</div>

<style>
	:global(.toast-body) {
		background-color: white;
	}

	:global(.toast-header, .toast-body) {
		border: 1px solid black;
	}

	.description {
		min-height: 1.5em;
	}

	.game-wrapper {
		display: grid;
		grid:
			[row1-start] "players game chat" [row1-end]
			/ 275px auto 275px;
		height: 100%;
	}

	.game-wrapper .game {
		grid-area: game;
		padding: 0px 48px;
		margin: 0px 5px;
		overflow-y: auto;
		overflow-x: hidden;
	}

	.game-wrapper .players {
		grid-area: players;
		padding: 16px;
		overflow-y: auto;
		border-right: 1px solid #dededf;
	}

	.game-wrapper .chat {
		grid-area: chat;
		min-height: 0; /* Fix scrolling */
		border-left: 1px solid #dededf;
		display: grid;
		grid:
			[row1-start] "chat-header" 64px [row1-end]
			[row2-start] "chat-messages" 1fr [row2-end]
			[row3-start] "chat-input" 64px [row3-end]
			/ auto;
		justify-content: center;
	}

	.game-wrapper .chat .info {
		grid-area: chat-header;
		border-bottom: 1px solid #dededf;
		text-align: center;
		font-size: 1.5em;
		color: #666;
		text-transform: uppercase;
		margin-top: 0.5em;
	}

	.game-wrapper .chat .messages {
		grid-area: chat-messages;
		padding: 16px;
		overflow-y: auto;
		overflow-x: hidden;
	}

	.game-wrapper .chat .messages :global(.message.info-message) {
		color: #666;
	}

	.game-wrapper .chat .messages :global(.message) {
		margin: 4px 8px;
	}

	.game-wrapper .chat .messages :global(.message:not(.info-message) b) {
		color: #bd2130;
	}

	.game-wrapper .chat input {
		grid-area: chat-input;
		margin: 16px;
		padding: 8px;
		border: none;
		border-radius: 5px;
		background-color: #f2f2f2;
		outline-color: #bd2130;
	}

	th,
	td {
		max-width: 150px;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	@media only screen and (max-width: 1200px) {
		.game-wrapper {
			display: block; /* Disable grid */
		}

		.game {
			padding: 15px !important;
			margin: 0px;
		}

		.players {
			display: grid;
			grid-template-columns: repeat(auto-fill, minmax(275px, 1fr));
			grid-gap: 1rem;
		}

		.players-header {
			margin-left: 1em;
		}
	}

	@media only screen and (min-width: 1200px) {
		.game::-webkit-scrollbar,
		.players::-webkit-scrollbar {
			width: 10px;
		}

		.game::-webkit-scrollbar-thumb,
		.players::-webkit-scrollbar-thumb {
			background-color: #646a7217;
		}

		.game::-webkit-scrollbar-thumb,
		.players::-webkit-scrollbar-thumb {
			background-color: #646a7217;
		}

		.players-header {
			display: none;
		}
	}
</style>
