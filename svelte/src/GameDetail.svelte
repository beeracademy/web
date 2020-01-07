<script>
	import CardCell from "./CardCell.svelte";
	import Chug from "./Chug.svelte";
	import PlayerStats from "./PlayerStats.svelte";
	import SipsGraph from "./SipsGraph.svelte";
	import TimeGraph from "./TimeGraph.svelte";

	let game_data = JSON.parse(document.getElementById("game_data").textContent);
	const ordered_gameplayers = JSON.parse(document.getElementById("ordered_gameplayers").textContent);

	async function updateData() {
		if (game_data.end_datetime || game_data.dnf) return;

		const res = await fetch(`/api/games/${game_data.id}/`);
		game_data = await res.json();
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
					end_datetime = new Date(game_data.cards.length[game_data.cards.length - 1].drawn_datetime);
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
</script>

<style>
	.description {
		min-height: 1.5em;
	}
</style>

<p class="description">{game_data.description}</p>

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

<h2>Players</h2>

<hr>

<div class="container">
<div class="row justify-content-md-center">
{#each ordered_gameplayers as gp, i}
<div class="col-md-auto">
	<div class="card">
		<a href="/players/{gp.user.id}/" style="margin: auto; display: flex; justify-content: center; align-items: center;">
			{#if gp.dnf}
			<div class="dnf-img-text">DNF</div>
			{/if}
			<img class="card-img-top" src="{gp.user.image_url}" alt="Card image cap">
		</a>
		<ul class="list-group list-group-flush">
			<li class="list-group-item">
				<a href="/players/{gp.user.id}/" class:dnf="{gp.dnf}">{gp.user.username}</a>
			</li>
			<PlayerStats player_stats={game_data.player_stats[i]} sips_per_beer={game_data.sips_per_beer}/>
		</ul>
	</div>
</div>
{/each}
</div>
</div>

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
<br>
<br>
<SipsGraph game_data={game_data} ordered_gameplayers={ordered_gameplayers}/>
<br>
<br>
<br>
<TimeGraph game_data={game_data} ordered_gameplayers={ordered_gameplayers}/>
