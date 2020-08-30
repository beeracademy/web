<script context="module">
	import { card_constants } from "./globals.js";
</script>

<script>
	export let start_datetime;
	export let chug;
	export let dnf;

	import ColoredSuit from "./ColoredSuit.svelte";

	const player = chug.player;
	$: card = chug.card;

	var intervalId = null;
	var durationStr;

	function start_delta_ms() {
		return Date.now() - new Date(start_datetime);
	}

	function updateDuration() {
		durationStr = window.formatDuration(start_delta_ms() - card.chug_start_start_delta_ms, 3);
	}

	$: {
		if (intervalId !== null) {
			clearInterval(intervalId);
		}

		if (card.chug_duration_ms) {
			durationStr = window.formatDuration(card.chug_duration_ms, 3);
		} else if (card.chug_start_start_delta_ms) {
			if (dnf) {
				durationStr = "DNF";
			} else {
				intervalId = setInterval(updateDuration, 10);
			}
		} else {
			durationStr = "Not started";
		}
	};
</script>

<style>
	.card-header {
		font-size: 4rem;
		text-align: center;
	}
</style>

<div class="col-md-auto">
	<div class="card">
		<div class="card-header">
			<ColoredSuit card={card}/>
		</div>
		<ul class="list-group list-group-flush">
			<li class="list-group-item">
				<a href="/players/{player.id}/">
					{player.username}
				</a>
			</li>
			<li class="list-group-item">
				{durationStr}
			</li>
			{#if card.chug_id}
			<li class="list-group-item staff-only">
				<a class="btn btn-primary text-light" href="/admin/games/chug/{card.chug_id}" style="width: 100%;">Edit</a>
			</li>
			{/if}
		</ul>
	</div>
</div>
