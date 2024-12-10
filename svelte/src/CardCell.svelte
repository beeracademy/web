<script module lang="ts">
import { card_constants } from "./globals";
</script>

<script lang="ts">
	import ColoredSuit from "./ColoredSuit.svelte";
	import { CardData } from "./types";

	interface Props {
		card: CardData | undefined;
	}

	let { card }: Props = $props();

	let valueName = $state(""),
		suitName = $state("");

	if (card) {
		valueName = card_constants.value_names[card.value];
		suitName = card_constants.suit_names[card.suit];
	}
</script>

{#if card}
	<td title="{valueName} of {suitName}">
		<span class="symbol">
			<ColoredSuit {card} />
		</span>
		{card.value}
	</td>
{:else}
	<td></td>
{/if}

<style>
	.symbol {
		width: 1rem;
		display: inline-block;
	}
</style>
