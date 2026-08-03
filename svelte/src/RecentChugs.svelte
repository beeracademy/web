<script module lang="ts">
import type { RecentChugData } from "./types";
</script>

<script lang="ts">
	import Chug from "./Chug.svelte";

    let chugs = $state(JSON.parse(
        document.getElementById("recent_chugs")!.textContent!
    ) as RecentChugData[]);
</script>

<div class="container">
	<div id="chugs_container" class="row justify-content-md-center">
		{#each chugs as chug}
			<Chug start_datetime={chug.game.start_datetime} chug={chug.chug} game_dnf={chug.game.dnf} game_id={chug.game.id} />
		{/each}
	</div>
</div>

<style>
	.container {
		margin-bottom: 2em;
	}
</style>
