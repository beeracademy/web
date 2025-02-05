<script module lang="ts">
import { formatDuration } from "./globals";
import type { ChugData } from "./types";
</script>

<script lang="ts">
	import ColoredSuit from "./ColoredSuit.svelte";
	interface Props {
		start_datetime: string;
		chug: ChugData;
		game_dnf: boolean;
	}

	let { start_datetime, chug, game_dnf }: Props = $props();

	const gameplayer = chug.gameplayer;
	const user = gameplayer.user;
	let card = $derived(chug.card);

	function getStartDeltaMs() {
		return Date.now() - new Date(start_datetime).getTime();
	}

	let startDeltaMs = $state(getStartDeltaMs());
	let { durationStr, inProgress } = $derived.by(() => {
		if (gameplayer.dnf) {
			return { durationStr: "DNF", inProgress: false };
		} else if (card.chug_duration_ms) {
			return { durationStr: formatDuration(card.chug_duration_ms, 3), inProgress: false };
		} else if (card.chug_start_start_delta_ms) {
			if (game_dnf) {
				return { durationStr: "DNF", inProgress: false };
			} else {
				return { durationStr: formatDuration(startDeltaMs - card.chug_start_start_delta_ms!, 3), inProgress: true };
			}
		} else {
			return { durationStr: "Not started", inProgress: false };
		}
	});
	let intervalId: ReturnType<typeof setInterval> | null = null;
	$effect(() => {
		if (inProgress) {
			intervalId = setInterval(() => {
				startDeltaMs = getStartDeltaMs();
			}, 10);
		} else {
			clearInterval(intervalId);
			intervalId = null;
		}
	});
</script>

<div class="col-md-auto">
	<div class="card">
		<div class="card-header">
			<ColoredSuit {card} />
		</div>
		<ul class="list-group list-group-flush">
			<li class="list-group-item">
				<a href="/players/{user.id}/" class="username">
					{user.username}
				</a>
			</li>
			<li class="list-group-item">
				{durationStr}
			</li>
			{#if card.chug_id}
				<li class="list-group-item staff-only">
					<a
						class="btn btn-primary text-light"
						href="/admin/games/chug/{card.chug_id}"
						style="width: 100%;">Edit</a
					>
				</li>
			{/if}
		</ul>
	</div>
</div>

<style>
	.card-header {
		font-size: 4rem;
		text-align: center;
	}
</style>
