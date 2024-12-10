<script lang="ts">
import type { PlayerStatsData } from "./types";

import { formatDuration, toBase14 } from "./globals";
interface Props {
	player_stats: PlayerStatsData;
}

const { player_stats }: Props = $props();

const ps: PlayerStatsData = $derived(player_stats);

function format(s: number, f?: (s: number) => string) {
	if (s === null) return "?";
	if (!f) return s;
	return f(s);
}
</script>

<div style="margin: 6px 0px; border-bottom: 1px solid #eee; display: flex;">
	<b>Total sips</b><span style="margin-left: auto;"
		>{format(ps.total_sips, toBase14)}<sub>14</sub></span
	>
</div>
<div style="margin: 6px 0px; border-bottom: 1px solid #eee; display: flex;">
	<b>Total time</b><span style="margin-left: auto;"
		>{format(ps.total_time, formatDuration)}</span
	>
</div>
<div style="margin: 6px 0px; border-bottom: 1px solid #eee; display: flex;">
	<b>Time per round</b><span style="margin-left: auto;"
		>{format(ps.time_per_turn, formatDuration)}</span
	>
</div>
<div style="margin: 6px 0px; border-bottom: 1px solid #eee; display: flex;">
	<b>Time per sip</b><span style="margin-left: auto;"
		>{format(ps.time_per_sip, formatDuration)}</span
	>
</div>
