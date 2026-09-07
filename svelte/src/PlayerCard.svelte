<script lang="ts">
import { formatDuration, toBase14 } from "./globals";
import type { GamePlayerData, PlayerStatsData } from "./types";

interface Props {
	gameplayer: GamePlayerData;
	player_stats: PlayerStatsData;
	colorIndex: number;
	rank: number;
	isCurrentTurn: boolean;
	done: boolean;
}

const {
	gameplayer,
	player_stats,
	colorIndex,
	rank,
	isCurrentTurn,
	done,
}: Props = $props();

const ps: PlayerStatsData = $derived(player_stats);

function format(s: number | null, f?: (s: number) => string) {
	if (s === null || s === undefined) return "?";
	if (!f) return s;
	return f(s);
}

const rankIcon = ["fa-crown", "fa-medal", "fa-medal", "fa-award"];
const rankClass = [
	"ranking-top-1",
	"ranking-top-2",
	"ranking-top-3",
	"ranking-top-neutral",
];
</script>

<div
	class={{"game-player-card": true, "current-turn": isCurrentTurn, "dnf": gameplayer.dnf}}
	style="--player-color: var(--player-{colorIndex % 6});"
>
	{#if done && rank}
		<span class="ranking-top-badge game-player-rank {rankClass[Math.min(rank, 4) - 1]}">
			<i class="fas {rankIcon[Math.min(rank, 4) - 1]}"></i> {rank}
		</span>
	{/if}

	<a href="/players/{gameplayer.user.id}/" class="game-player-head">
		<div class="round-image game-player-avatar" style="background-image: url({gameplayer.user.image_url});"></div>
		<div class="username game-player-name {gameplayer.dnf ? 'dnf' : ''}">
			{gameplayer.user.username}
		</div>
	</a>

	<div class="game-player-stats">
		<div class="game-stat-row">
			<span class="game-stat-label">Total sips</span>
			<span class="game-stat-value">{format(ps.total_sips, toBase14)}<sub>14</sub></span>
		</div>
		<div class="game-stat-row">
			<span class="game-stat-label">Total time</span>
			<span class="game-stat-value">{format(ps.total_time, (v) => formatDuration(v))}</span>
		</div>
		<div class="game-stat-row">
			<span class="game-stat-label">Time / round</span>
			<span class="game-stat-value">{format(ps.time_per_turn, (v) => formatDuration(v))}</span>
		</div>
		<div class="game-stat-row">
			<span class="game-stat-label">Time / sip</span>
			<span class="game-stat-value">{format(ps.time_per_sip, (v) => formatDuration(v))}</span>
		</div>
	</div>
</div>

<style>
	.game-player-card {
		position: relative;
		background-color: var(--color-surface-2);
		border: 1px solid var(--color-border);
		border-top: 3px solid var(--player-color);
		border-radius: var(--radius-lg);
		padding: 1rem;
		transition:
			border-color 0.15s ease,
			box-shadow 0.15s ease;
	}

	.game-player-card.current-turn {
		border-color: var(--color-primary);
		box-shadow: 0 0 0 1px rgba(172, 24, 28, 0.4);
	}

	.game-player-card.dnf {
		opacity: 0.6;
	}

	.game-player-rank {
		position: absolute;
		top: 0.75rem;
		right: 0.75rem;
		width: auto;
		gap: 0.3rem;
		padding: 0.15rem 0.55rem;
		font-size: 0.75rem;
	}

	.game-player-head {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-bottom: 0.5rem;
		color: var(--color-text) !important;
		text-decoration: none !important;
	}

	.game-player-avatar {
		width: 40px;
		height: 40px;
		flex: none;
	}

	.game-player-name {
		font-weight: 700;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.game-player-stats {
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
	}

	.game-stat-row {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		font-size: 0.82rem;
		padding-top: 0.4rem;
		border-top: 1px solid var(--color-border);
	}

	.game-stat-row:first-child {
		padding-top: 0;
		border-top: none;
	}

	.game-stat-label {
		color: var(--color-text-muted);
	}

	.game-stat-value {
		font-family: var(--font-mono);
		font-weight: 600;
		color: var(--color-text);
	}
</style>
