import { mount } from "svelte";
import GameDetail from "./GameDetail.svelte";

const target = document.querySelector("#svelte-game_detail");

export default mount(GameDetail, {
	target,
});
