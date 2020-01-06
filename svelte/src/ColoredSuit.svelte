<script context="module">
	import { card_constants } from "./globals.js";
</script>

<script>
	export let card;

	const [symbol, color] = card_constants.suit_symbols[card.suit];
</script>

<span style="color: {color};">{symbol}</span>
