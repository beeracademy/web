import { mount } from "svelte";
import GameDetail from "./GameDetail.svelte";

const target = document.querySelector("#svelte-game_detail");

// biome-ignore lint/suspicious/noExplicitAny: YOLO
(window as any).GameDetail_init = () => {
	mount(GameDetail, {
		target,
	});
};
