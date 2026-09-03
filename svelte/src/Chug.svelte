<script module lang="ts">
import { formatDateWithoutTime, formatDuration } from "./globals";
import type { ChugData } from "./types";
</script>

<script lang="ts">
	import ColoredSuit from "./ColoredSuit.svelte";
	interface Props {
		start_datetime: string;
		chug: ChugData;
		game_dnf: boolean;
		game_id?: number,
	}

	let { start_datetime, chug, game_dnf, game_id }: Props = $props();

	const gameplayer = chug.gameplayer;
	const user = gameplayer.user;
	let card = $derived(chug.card);

	function getStartDeltaMs() {
		return Date.now() - new Date(start_datetime).getTime();
	}

	const chugStartDate = new Date(new Date(start_datetime).getTime() + (card.chug_start_start_delta_ms ?? 0));

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

<div class={{"chug-card": true, "in-progress": inProgress}}>
	<div class="chug-card-suit">
		<ColoredSuit {card} />
	</div>
	{#if user}
		<a href="/players/{user.id}/" class="username chug-card-user">
			{user.username}
		</a>
	{/if}
	<div class="chug-card-duration text-mono">
		{durationStr}
	</div>
	{#if game_id}
		<a href="/games/{game_id}" class="chug-card-date">{formatDateWithoutTime(chugStartDate)}</a>
	{/if}
	{#if card.chug_id}
		<a
			class="btn btn-outline-secondary btn-sm staff-only chug-card-edit"
			href="/admin/games/chug/{card.chug_id}">Edit</a
		>
	{/if}
</div>

<style>
	.chug-card {
		display: flex;
		flex-direction: column;
		align-items: center;
		text-align: center;
		gap: 0.35rem;
		padding: 1rem 0.75rem;
		background-color: var(--color-surface-2);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-lg);
	}

	.chug-card.in-progress {
		border-color: rgba(172, 24, 28, 0.4);
		box-shadow: 0 0 0 1px rgba(172, 24, 28, 0.3);
	}

	.chug-card-suit {
		font-size: 2.5rem;
		line-height: 1;
	}

	.chug-card-user {
		font-weight: 700;
	}

	.chug-card-duration {
		color: var(--color-text-muted);
		font-size: 0.85rem;
	}

	.chug-card-date {
		font-size: 0.78rem;
	}

	.chug-card-edit {
		margin-top: 0.35rem;
	}
</style>
