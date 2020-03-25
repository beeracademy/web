<script>
	import { onMount } from 'svelte';

	import Players from "./Players.svelte";
	import CardCell from "./CardCell.svelte";
	import Chug from "./Chug.svelte";
	import SipsGraph from "./SipsGraph.svelte";
	import TimeGraph from "./TimeGraph.svelte";

	let game_data = JSON.parse(document.getElementById("game_data").textContent);
	const ordered_gameplayers = JSON.parse(document.getElementById("ordered_gameplayers").textContent);

	async function updateData() {
		if (game_data.end_datetime || game_data.dnf) return;

		try {
			const res = await fetch(`/api/games/${game_data.id}/`);
			game_data = await res.json();
		} catch(e) {}

		setTimeout(updateData, 1000);
	}

	updateData();

	let duration = null;
	$: {
		let end_datetime;
		if (game_data.end_datetime) {
			end_datetime = new Date(game_data.end_datetime);
		} else {
			if (game_data.dnf) {
				if (game_data.cards.length === 0) {
					end_datetime = new Date(game_data.start_datetime);
				} else {
					end_datetime = new Date(game_data.cards[game_data.cards.length - 1].drawn_datetime);
				}
			} else {
				end_datetime = Date.now();
			}
		}
		if (game_data.start_datetime) {
			const start_datetime = new Date(game_data.start_datetime);
			duration = end_datetime - start_datetime;
		}
	}

	let chugs;
	$: {
		chugs = [];
		for (let i = 0; i < game_data.cards.length; i++) {
			const card = game_data.cards[i];
			if (card.value === 14) {
				chugs.push({
					card: card,
					player: ordered_gameplayers[i % ordered_gameplayers.length].user,
				});
			}
		}
	}

	$: game_data, game_data.playerCount = ordered_gameplayers.length;

	let chat_messages, chat_input;
	onMount(function () {
		var scheme = window.location.protocol === "https:"? "wss": "ws";

		var socket = null;

		startSocket();

		function startSocket() {
			socket = new WebSocket(scheme + "://" + window.location.host + "/ws/chat/" + game_data.id + "/");

			socket.addEventListener("open", function (e) {
				if (window.is_authenticated) {
					chat_input.disabled = false;
				}
			});

			socket.addEventListener("close", function(e) {
				console.error("Chat socket closed unexpectedly!");
				disconnected();
			});

			socket.addEventListener("error", function(e) {
				console.error("Got an error from the chat socket!");
				disconnected();
			});

			socket.addEventListener("message", function (e) {
				var data = JSON.parse(e.data);

				var username = data["username"];
				if (!username) {
					username = "Guest";
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

					addMessage(username, message, isInfo, time)
				} else {
					console.error("Unknown message received:");
					console.error(data);
				}
			});
		}

		chat_input.addEventListener("keyup", function(e) {
			if (e.keyCode === 13) {
				socket.send(JSON.stringify({
					"message": chat_input.value,
				}));

				chat_input.value = "";
			}
		});

		function disconnected() {
			chat_input.disabled = true;
			setTimeout(startSocket, 1000);
		}

		function addMessage(user, msg, isInfo, time) {
			var elm = document.createElement("div");
			elm.classList += "message";

			if (isInfo) {
				elm.classList += " info-message";
			}

			var userElm = document.createElement("B");
			userElm.innerText = user;
			if (!isInfo) {
				userElm.innerText += ":";
			}
			userElm.innerText += " ";
			elm.appendChild(userElm);

			var textElm = document.createTextNode(msg);
			elm.appendChild(textElm)

			chat_messages.appendChild(elm);
		}
	});
</script>

<style>
	.description {
		min-height: 1.5em;
	}

    .game-wrapper {
        display: flex;
        flex: 1;
        overflow: hidden;
    }

    .game-wrapper .game {
        flex: 1;
        padding: 0px 48px;
        margin: 0px 5px;
        overflow-y: auto;
        overflow-x: hidden;
    }

    .game-wrapper .chat, .game-wrapper .players {
        width: 340px;
        display: flex;
        flex-direction: column;
    }

    .game-wrapper .players {
        padding: 16px;
        overflow-y: auto;
        border-right: 1px solid #dededf;
    }

    .game-wrapper .chat {
        border-left: 1px solid #dededf;
    }

    .game-wrapper .chat .info {
        height: 64px;
        border-bottom: 1px solid #dededf;
        display: flex;
        justify-content: center;
        align-items: center;
        font-size: 1.5em;
        color: #666;
        text-transform: uppercase;

    }

    .game-wrapper .chat .messages {
        display: flex;
        flex: 1;
        padding: 16px;
        justify-content: flex-end;
        flex-direction: column;
        overflow-y: auto;
        overflow-x: hidden;
    }

    .game-wrapper .chat .messages .message.info-message {
        color: #666;
    }

    .game-wrapper .chat .messages .message {
        margin: 4px 8px;
    }

    .game-wrapper .chat .messages .message:not(.info-message) b {
        color: #bd2130;
    }

    .game-wrapper .chat input {
        margin: 16px;
        padding: 8px;
        border: none;
        border-radius: 5px;
        background-color: #f2f2f2;
        outline-color: #bd2130;
    }

    .card-img-top {
		/* IMAGE_WIDTH: */
        width: 156px;
    }

    @media only screen and (max-width: 600px) {
        .chat, .players {
            display: none !important;
        }

        .game {
            padding: 15px !important;
            margin: 0px;
        }
    }

    @media only screen and (min-width: 600px) {
        .game::-webkit-scrollbar, .players::-webkit-scrollbar {
            width: 10px;
        }

        .game::-webkit-scrollbar-track, .players::-webkit-scrollbar-track {
         background: transparent;
        }

        .game::-webkit-scrollbar-thumb, .players::-webkit-scrollbar-thumb {
            background-color: #646a7217;
        }
    }
</style>

<div class="game-wrapper">
	<div class="players">
		<Players game_data={game_data} ordered_gameplayers={ordered_gameplayers}/>
	</div>
	<div class="game">
		<div class="container">
			<h2>
				Meta
		        {#if window.is_staff}
                <a class="btn btn-primary float-right text-light col-md-auto" href="/admin/games/game/{game_data.id}/change/">Edit</a>
                <br><br class="d-lg-none">
				{/if}
			</h2>

			<hr>

			<p class="description">{@html game_data.description_html}</p>

			<table class="table">
			<thead>
				<tr>
				<th scope="col">Game id</th>
				<th scope="col">Start Time</th>
				<th scope="col">End Time</th>
				<th scope="col">Duration</th>
				</tr>
			</thead>
			<tbody>
				<tr>
				<td>{game_data.id}</td>
				<td id="game_start_datetime">
					{#if game_data.start_datetime}
						{window.formatDate(new Date(game_data.start_datetime))}
					{:else}
						?
					{/if}
				</td>
				<td id="game_end_datetime">
					{#if game_data.dnf}
						DNF
					{:else if game_data.end_datetime}
						{window.formatDate(new Date(game_data.end_datetime))}
					{:else}
						-
					{/if}
				</td>
				<td id="game_duration">
					{#if duration}
						{window.formatDuration(duration)}
					{:else}
						?
					{/if}
				</td>
				</tr>
			</tbody>
			</table>

			<h2>Chugs</h2>

			<hr>

			<div class="container">
				<div id="chugs_container" class="row justify-content-md-center">
					{#each chugs as chug}
					<Chug chug={chug}/>
					{/each}
				</div>
			</div>

			<h2>Round overview</h2>

			<hr>

			<table id="cards_table" class="table table-bordered table-striped table-hover table-sm">
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
						<CardCell card={game_data.cards[i * ordered_gameplayers.length + j]} />
						{/each}
					</tr>
					{/each}
				</tbody>
			</table>

			<h2>Graphs</h2>

			<hr>

			<br>
			<br>
			<SipsGraph game_data={game_data} ordered_gameplayers={ordered_gameplayers}/>
			<br>
			<br>
			<br>
			<TimeGraph game_data={game_data} ordered_gameplayers={ordered_gameplayers}/>
		</div>
	</div>

	<div class="chat">
        <div class="info">
            Chat
        </div>
		<div class="messages" id="chat-messages" bind:this={chat_messages}>
        </div>
		<input id="chat-input" autocomplete="off" type="text" disabled
			placeholder={window.is_authenticated? "Send a message": "Login to chat"} bind:this={chat_input}>
	</div>
</div>
