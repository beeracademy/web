<script module lang="ts">
import { formatDate, formatDuration, is_staff } from "./globals";
import type { ChugData, GameData, GamePlayerData } from "./types";
</script>

<script lang="ts">
	import Map from "./Map.svelte";
	import Image from "./Image.svelte";
	import PlayerCard from "./PlayerCard.svelte";
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
	let done = $derived(game_data.end_datetime !== null || game_data.dnf);

	async function updateData() {
		if (done) return;

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

	let currentTurn: number | undefined = $derived.by(() => {
		if (done) {
			return undefined;
		}

		const n = game_data.cards.length;
		if (n === 0) {
			return 0;
		}

		const lastCard = game_data.cards[n - 1];
		let index = n;
		if (lastCard.value === 14 && lastCard.chug_duration_ms === null) {
			index--;
		}
		return index % ordered_gameplayers.length;
	});

	const numPlayers = ordered_gameplayers.length;
	const totalCards = numPlayers * 13;

	let currentRound = $derived(
		Math.min(13, Math.floor(game_data.cards.length / numPlayers) + 1)
	);
	let currentCard = $derived(Math.min(totalCards, game_data.cards.length + 1));

	let rankedPlayerIndices: number[] = $derived.by(() => {
		return ordered_gameplayers
			.map((_, i) => i)
			.sort((a, b) => {
				const sa = game_data.player_stats[a]?.total_sips ?? 0;
				const sb = game_data.player_stats[b]?.total_sips ?? 0;
				return sb - sa;
			});
	});

	let ranks: number[] = $derived.by(() => {
		const r = new Array(numPlayers).fill(0);
		rankedPlayerIndices.forEach((playerIndex, rank) => {
			r[playerIndex] = rank + 1;
		});
		return r;
	});

	let statusLabel = $derived.by(() => {
		if (game_data.dnf) return "DNF";
		if (game_data.end_datetime) return "Finished";
		if (game_data.start_datetime) return "Live";
		return "Not started";
	});

	type TabId = "rounds" | "sips" | "time";
	let activeTab: TabId = $state("rounds");
	const tabs: { id: TabId; label: string; icon: string }[] = [
		{ id: "rounds", label: "Round overview", icon: "fa-table" },
		{ id: "sips", label: "Sips per round", icon: "fa-chart-line" },
		{ id: "time", label: "Time per turn", icon: "fa-chart-line" },
	];

	let lightboxOpen = $state(false);

	function openLightbox() {
		lightboxOpen = true;
		document.body.classList.add("gallery-lightbox-active");
	}

	function closeLightbox() {
		lightboxOpen = false;
		document.body.classList.remove("gallery-lightbox-active");
	}

	function handleLightboxKeydown(e: KeyboardEvent) {
		if (lightboxOpen && e.key === "Escape") {
			closeLightbox();
		}
	}
</script>

<svelte:window onkeydown={handleLightboxKeydown} />

<div class="page-toolbar" style="align-items: center;">
	<div>
		<h1 class="page-title icon-heading">
			<i class="fas fa-gamepad"></i> Game #{game_data.id}
		</h1>
		<p class="page-subtitle icon-heading-inline">
			{#if game_data.start_datetime}
				Started {formatDate(new Date(game_data.start_datetime))}
			{/if}
		</p>
	</div>
	<div class="page-toolbar-actions">
		{#if statusLabel === "Live"}
			<span class="game-live-badge"><span class="status-dot"></span> Live</span>
		{:else if statusLabel === "DNF"}
			<span class="game-status-badge game-status-dnf">DNF</span>
		{/if}
		{#if is_staff}
			<a class="btn btn-outline-secondary btn-sm" href="/admin/games/game/{game_data.id}/change/">
				<i class="fas fa-user-edit"></i> Edit
			</a>
		{/if}
	</div>
</div>

{#if !done}
	{#if game_data.description_html}
		<p class="description">{@html game_data.description_html}</p>
	{/if}

	<div class="stat-grid game-stat-grid stats-summary-grid">
		<div class="stat-card-v2">
			<div class="stat-card-v2-head">
				<span class="stat-card-v2-label">Round</span>
			</div>
			<div class="stat-card-v2-value">{currentRound}<span class="stat-card-v2-value-sub">/13</span></div>
			<div class="stats-card-subtext">Card {currentCard} of {totalCards}</div>
			<i class="fas fa-layer-group stat-card-v2-icon"></i>
		</div>
		<div class="stat-card-v2">
			<div class="stat-card-v2-head">
				<span class="stat-card-v2-label">Duration</span>
			</div>
			<div class="stat-card-v2-value">{#if duration}{formatDuration(duration)}{:else}?{/if}</div>
			<div class="stats-card-subtext">
				{#if durationSinceLastActivity !== null && currentTurn !== undefined}
					{formatDuration(durationSinceLastActivity)} waiting for {ordered_gameplayers[currentTurn].user.username}
				{:else}
					In progress
				{/if}
			</div>
			<i class="fas fa-stopwatch stat-card-v2-icon"></i>
		</div>
	</div>
{:else if game_data.image !== null || game_data.description_html || !game_data.dnf}
	<div class="game-summary-row">
		{#if game_data.image !== null}
			<button type="button" class="card game-summary-card game-summary-image-card" onclick={openLightbox}>
				<img src={game_data.image} alt="Game" />
			</button>
		{/if}
		{#if game_data.description_html}
			<div class="card game-summary-card game-summary-description-card">
				<p class="description">{@html game_data.description_html}</p>
			</div>
		{/if}
		{#if !game_data.dnf}
			<div class="card game-summary-card stat-card-v2 no-accent">
				<div class="stat-card-v2-head">
					<span class="stat-card-v2-label">Duration</span>
				</div>
				<div class="stat-card-v2-value">{#if duration}{formatDuration(duration)}{:else}?{/if}</div>
				<div class="stats-card-subtext">
					{#if game_data.end_datetime}
						Ended {formatDate(new Date(game_data.end_datetime))}
					{/if}
				</div>
				<i class="fas fa-stopwatch stat-card-v2-icon"></i>
			</div>
		{/if}
	</div>
{/if}

{#if game_data.image !== null}
	<div class="gallery-lightbox" class:open={lightboxOpen} onclick={(e) => { if (e.target === e.currentTarget) closeLightbox(); }}>
		<button type="button" class="gallery-lightbox-close" aria-label="Close" onclick={closeLightbox}>&times;</button>
		<div class="gallery-lightbox-inner">
			<img class="gallery-lightbox-image" src={game_data.image} alt="Game" />
		</div>
	</div>
{/if}

<div class="card section-card">
	<div class="section-card-header">
		<h2 class="icon-heading"><i class="fas fa-users"></i> Players</h2>
	</div>
	<div class="game-players-grid">
		{#each ordered_gameplayers as gp, i}
			<PlayerCard
				gameplayer={gp}
				player_stats={game_data.player_stats[i]}
				colorIndex={i}
				rank={ranks[i]}
				isCurrentTurn={i === currentTurn}
				{done}
			/>
		{/each}
	</div>
</div>

<div class="card section-card">
	<ul class="nav nav-tabs game-detail-tabs">
		{#each tabs as tab}
			<li class="nav-item">
				<button
					type="button"
					class="nav-link{activeTab === tab.id ? ' active' : ''}"
					onclick={() => (activeTab = tab.id)}
				>
					<i class="fas {tab.icon}"></i> {tab.label}
				</button>
			</li>
		{/each}
	</ul>

	{#if activeTab === "rounds"}
		<div class="table-card mb-0">
			<div class="table-responsive">
				<table
					id="cards_table"
					class="table academy-table slim mb-0"
				>
					<thead>
						<tr>
							<th scope="col">Round</th>
							{#each ordered_gameplayers as gp, i}
								<th scope="col" class={{"current-turn-col": i === currentTurn}}>{gp.user.username}</th>
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
			</div>
		</div>
	{:else if activeTab === "sips"}
		<SipsGraph {game_data} {ordered_gameplayers} />
	{:else if activeTab === "time"}
		<TimeGraph {game_data} {ordered_gameplayers} />
	{/if}
</div>

<div class="card section-card">
	<div class="section-card-header">
		<h2 class="icon-heading"><i class="fas fa-wine-bottle"></i> Chugs</h2>
	</div>
	{#if chugs.length > 0}
		<div class="chugs-grid">
			{#each chugs as chug}
				{#if game_data.start_datetime}
					<Chug start_datetime={game_data.start_datetime} {chug} game_dnf={game_data.dnf} />
				{/if}
			{/each}
		</div>
	{:else}
		<p class="empty-state">No chugs yet.</p>
	{/if}
</div>

{#if game_data.location.latitude !== null}
	<div class="card section-card">
		<div class="section-card-header">
			<h2 class="icon-heading"><i class="fas fa-map-marker-alt"></i> Location</h2>
		</div>
		<div class="stats-map">
			<Map location={game_data.location} />
		</div>
	</div>
{/if}

{#if game_data.image !== null && !done}
	<div class="card section-card">
		<div class="section-card-header">
			<h2 class="icon-heading"><i class="fas fa-image"></i> Image</h2>
		</div>
		<Image url={game_data.image} />
	</div>
{/if}

<style>
	.description {
		color: var(--color-text-muted);
		margin-top: -0.5rem;
	}

	.game-stat-grid {
		grid-template-columns: repeat(2, 1fr);
	}

	.game-stat-grid .stat-card-v2::before {
		display: none;
	}

	.stat-card-v2-value-sub {
		font-size: 1.1rem;
		color: var(--color-text-muted);
	}

	.game-summary-row {
		display: flex;
		flex-wrap: wrap;
		gap: 1.25rem;
		margin-bottom: 1.25rem;
	}

	.game-summary-card {
		flex: 1 1 240px;
		margin-bottom: 0;
		min-width: 0;
	}

	.game-summary-image-card {
		padding: 0;
		overflow: hidden;
		display: flex;
		border: 1px solid var(--color-border);
		cursor: pointer;
		transition: opacity 0.15s ease;
	}

	.game-summary-image-card:hover {
		opacity: 0.85;
	}

	.game-summary-image-card img {
		width: 100%;
		height: 100%;
		max-height: 200px;
		object-fit: cover;
		display: block;
	}

	.stat-card-v2.no-accent::before {
		display: none;
	}

	.game-summary-description-card {
		display: flex;
		align-items: center;
		padding: 1.25rem 1.5rem;
	}

	.game-summary-description-card .description {
		margin: 0;
	}

	.game-players-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
		gap: 1rem;
	}

	.chugs-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
		gap: 1rem;
	}

	.game-detail-tabs {
		margin-bottom: 1.25rem;
		flex-wrap: wrap;
	}

	.game-detail-tabs .nav-link {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		background: none;
		cursor: pointer;
	}

	:global(.current-turn-col) {
		color: var(--color-primary) !important;
	}

	@media (max-width: 768px) {
		.game-stat-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
