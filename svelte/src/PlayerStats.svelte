<script>
	export let player_stats;
	export let sips_per_beer;

	let ps;
	$: ps = player_stats;

	function format(s, f) {
		if (s === null) return "?";
		if (!f) return s;
		return f(s);
	}

	const round2 = n => Math.round(n, 2);
</script>

<div style="margin: 6px 0px; border-bottom: 1px solid #eee; display: flex;">
	<b>Total sips</b><span style="margin-left: auto;">{format(ps.total_sips)}</span>
</div>
<div style="margin: 6px 0px; border-bottom: 1px solid #eee; display: flex;">
	<b>Total beers</b><span style="margin-left: auto;">{format(ps.full_beers)}</span>
	<div style="margin-left: 6px;">
		<sup><span>{format(ps.extra_sips)}</span></sup>&frasl;<sub>{sips_per_beer}</sub>
	</div>
</div>
<div style="margin: 6px 0px; border-bottom: 1px solid #eee; display: flex;">
	<b>Total time</b><span style="margin-left: auto;">{format(ps.total_time, window.formatDuration)}</span>
</div>
<div style="margin: 6px 0px; border-bottom: 1px solid #eee; display: flex;">
	<b>Time per round</b><span style="margin-left: auto;">{format(ps.time_per_turn, window.formatDuration)}</span>
</div>
<div style="margin: 6px 0px; border-bottom: 1px solid #eee; display: flex;">
	<b>Time per sip</b><span style="margin-left: auto;">{format(ps.time_per_sip, window.formatDuration)}</span>
</div>