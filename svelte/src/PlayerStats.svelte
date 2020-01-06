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

<li class="list-group-item">Total sips: <span>{format(ps.total_sips)}</span></li>
<li class="list-group-item">Sips per turn: <span>{format(ps.sips_per_turn, round2)}</span></li>
<li class="list-group-item">Total beers: <span>{format(ps.full_beers)}</span> <sup><span>{format(ps.extra_sips)}</span></sup>&frasl;<sub>{sips_per_beer}</sub></li>
<li class="list-group-item">Total time: <span>{format(ps.total_time, window.formatDuration)}</span></li>
<li class="list-group-item">Time per round: <span>{format(ps.time_per_turn, window.formatDuration)}</span></li>
<li class="list-group-item">Time per sip: <span>{format(ps.time_per_sip, window.formatDuration)}</span></li>
