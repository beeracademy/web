<script module lang="ts">
import type { RecentChugData } from "./types";
</script>

<script lang="ts">
	import Chug from "./Chug.svelte";

    let chugs = $state(JSON.parse(
        document.getElementById("recent_chugs")!.textContent!
    ) as RecentChugData[]);
</script>

<div class="recent-chugs-grid">
	{#each chugs as chug}
		<Chug start_datetime={chug.game.start_datetime} chug={chug.chug} game_dnf={chug.game.dnf} game_id={chug.game.id} />
	{/each}
</div>

<style>
	.recent-chugs-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
		gap: 1rem;
	}
</style>
