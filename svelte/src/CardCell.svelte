<svelte:options immutable/>

<script context="module">
	import { card_constants } from "./globals.js";
</script>

<script>
	export let card;

	import ColoredSuit from "./ColoredSuit.svelte";

	let valueName, suitName;

	if (card) {
		valueName = card_constants.value_names[card.value];
		suitName = card_constants.suit_names[card.suit];
	}
</script>

<style>
.symbol {
    width: 1rem;
    display: inline-block;
}
</style>

{#if card}
<td title="{valueName} of {suitName}">
	<span class="symbol">
		<ColoredSuit card={card}/>
	</span>
	{card.value}
</td>
{:else}
<td></td>
{/if}
