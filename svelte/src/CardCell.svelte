<script context="module">
	import { card_constants } from "./globals.js";
</script>

<script>
	export let card;

	import ColoredSuit from "./ColoredSuit.svelte";

	let cardName, symbol, color;

	if (card) {
		cardName = `${card_constants.value_names[card.value]} of ${card_constants.suit_names[card.suit]}`;
	}
</script>

<style>
.symbol {
    width: 1rem;
    display: inline-block;
}
</style>

{#if card}
<td title={cardName}>
	<span class="symbol">
		<ColoredSuit card={card}/>
	</span>
	{card.value}
</td>
{:else}
<td></td>
{/if}
