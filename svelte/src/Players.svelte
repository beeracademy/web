<script lang="ts">
import PlayerStats from "./PlayerStats.svelte";
import type { GameData, GamePlayerData } from "./types";

interface Props {
	game_data: GameData;
	ordered_gameplayers: GamePlayerData[];
}

const { game_data, ordered_gameplayers }: Props = $props();
</script>

{#each ordered_gameplayers as gp, i}
	<div class="card" style="margin-bottom: 16px;">
		<div class="card-body">
			<a href="/players/{gp.user.id}/">
				<div style="display: flex; align-items: center; margin-bottom: 12px;">
					<div
						class="round-image"
						style="background-image: url({gp.user
							.image_url}); margin-right: 16px;"
></div>
					<div
						class="username {gp.dnf ? 'dnf' : ''}"
						style="flex: 1; font-weight: bold; text-align:right; white-space: nowrap; overflow: hidden; text-overflow: ellipsis"
					>
						{gp.user.username}
					</div>
				</div>
			</a>
			<div style="display: flex; flex-direction: column;">
				<PlayerStats
					player_stats={game_data.player_stats[i]}
				/>
			</div>
		</div>
	</div>
{/each}

<style>
	.dnf {
		text-decoration: line-through;
	}

	.card {
		min-width: 225px;
		margin: auto;
	}
</style>
