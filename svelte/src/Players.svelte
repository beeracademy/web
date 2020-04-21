<script>
	import PlayerStats from "./PlayerStats.svelte";

    export let game_data;
    export let ordered_gameplayers;
</script>

<style>
    .dnf {
        text-decoration: line-through;
    }
</style>

{#each ordered_gameplayers as gp, i}
    <div class="card" style="margin-bottom: 16px; width: 100%;">
        <div class="card-body">
        <a href="/players/{gp.user.id}/">
            <div style="display: flex; align-items: center; margin-bottom: 12px;">
                <div class="round-image" style="background-image: url({gp.user.image_url}); margin-right: 16px;"></div>
                <div class="username {gp.dnf ? 'dnf' : ''}" style="flex: 1; font-weight: bold; text-align:right; white-space: nowrap; overflow: hidden; text-overflow: ellipsis">{gp.user.username}</div>
            </div>
        </a>
            <div style="display: flex; flex-direction: column;">
                <PlayerStats player_stats={game_data.player_stats[i]} sips_per_beer={game_data.sips_per_beer}/>
            </div>
        </div>
    </div>    
{/each}
