<script context="module">
	import { card_constants } from "./globals.js";
</script>

<script>
	export let chug;

	import ColoredSuit from "./ColoredSuit.svelte";

	const {card, player} = chug;
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
				{window.formatDuration(card.chug_duration_ms, 3)}
			</li>
			<li class="list-group-item staff-only">
				<a class="btn btn-primary text-light" href="/admin/games/chug/{card.chug_id}" style="width: 100%;">Edit</a>
			</li>
		</ul>
	</div>
</div>
