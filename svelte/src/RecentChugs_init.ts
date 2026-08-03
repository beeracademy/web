import { mount } from "svelte";
import RecentChugs from "./RecentChugs.svelte";

const target = document.querySelector("#svelte-recent_chugs");

// biome-ignore lint/suspicious/noExplicitAny: YOLO
(window as any).RecentChugs_init = () => {
	mount(RecentChugs, {
		target,
	});
};
