<script lang="ts">
import { onDestroy, onMount, tick } from "svelte";
import { type EmojiCategory, type EmojiItem, loadEmojiData } from "./emojiData";
import { current_user, userColors } from "./globals";
import type { ChatMessage, ChatUser, GamePlayerData } from "./types";

interface Props {
	game_id: number;
	ordered_gameplayers: GamePlayerData[];
	isOpen?: boolean;
	unreadCount?: number;
}

let {
	game_id,
	ordered_gameplayers,
	isOpen = $bindable(false),
	unreadCount = $bindable(0),
}: Props = $props();

let messages: ChatMessage[] = $state([]);
let inputText = $state("");
let showEmojiPicker = $state(false);
let connectionStatus: "connecting" | "connected" | "disconnected" =
	$state("connecting");
let myChatId: string | null = $state(null);

let onlineUsers: ChatUser[] = $state([]);
let showOnlinePopover = $state(false);

let onlineCount = $derived(
	Math.max(onlineUsers.length, connectionStatus === "connected" ? 1 : 0),
);

let onlineUsersList = $derived.by(() => {
	const list =
		onlineUsers.length > 0
			? [...onlineUsers]
			: myChatId
				? [
						{
							chat_id: myChatId,
							username: current_user?.username,
							user_id: current_user?.id,
						},
					]
				: [];

	return list.map((u) => {
		const isMe = u.chat_id === myChatId;
		const rawName = u.username?.trim();
		const playerIndex = ordered_gameplayers.findIndex(
			(p) =>
				(u.user_id && p.user.id === u.user_id) ||
				(rawName && p.user.username.toLowerCase() === rawName.toLowerCase()),
		);
		const isPlayer = playerIndex !== -1;
		const color = isPlayer
			? userColors[playerIndex % userColors.length]
			: "var(--color-text)";

		let displayName = "";
		if (isPlayer) {
			displayName =
				ordered_gameplayers[playerIndex].user.username + (isMe ? " (You)" : "");
		} else if (rawName) {
			displayName = rawName + (isMe ? " (You)" : "");
		} else if (u.is_game) {
			displayName = "Game Display";
		} else {
			displayName = isMe ? "You (Guest)" : "Spectator";
		}

		return {
			...u,
			displayName,
			isPlayer,
			playerIndex,
			color,
			isMe,
		};
	});
});

let messagesContainer: HTMLElement | null = $state(null);
let inputElement: HTMLInputElement | null = $state(null);
let socket: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let isDestroyed = false;

let prevOpen = false;
$effect(() => {
	if (isOpen) {
		if (!prevOpen) {
			const currentScroll =
				window.scrollY || document.documentElement.scrollTop;
			document.body.classList.add("game-chat-open");
			unreadCount = 0;
			showEmojiPicker = false;
			scrollToBottom();
			if (window.innerWidth >= 1280) {
				tick().then(() => {
					const layout = document.querySelector(".site-main-layout");
					if (layout) {
						layout.scrollTop = currentScroll;
					}
				});
			}
			setTimeout(() => {
				inputElement?.focus();
			}, 150);
			prevOpen = true;
		}
	} else {
		if (prevOpen) {
			let currentScroll = 0;
			if (window.innerWidth >= 1280) {
				const layout = document.querySelector(".site-main-layout");
				if (layout) {
					currentScroll = layout.scrollTop;
				}
			}
			document.body.classList.remove("game-chat-open");
			showEmojiPicker = false;
			showOnlinePopover = false;
			if (window.innerWidth >= 1280) {
				tick().then(() => {
					window.scrollTo(0, currentScroll);
				});
			}
			prevOpen = false;
		}
	}
});

let emojiSearchQuery = $state("");
let selectedCategory = $state("smileys");
let hoveredEmoji: EmojiItem | null = $state(null);
let emojiSearchInput: HTMLInputElement | null = $state(null);

// Lazily loaded emoji data — populated on first picker open
let emojiCategories: EmojiCategory[] = $state([]);
let allEmojis: EmojiItem[] = $state([]);
let emojiDataLoaded = $state(false);

let searchResults = $derived.by(() => {
	const q = emojiSearchQuery.trim().toLowerCase();
	if (!q) return [];
	const tokens = q.split(/\s+/);
	const matches: EmojiItem[] = [];
	for (const item of allEmojis) {
		if (tokens.every((t) => item.k.includes(t))) {
			matches.push(item);
			if (matches.length >= 140) break;
		}
	}
	return matches;
});

let currentDisplayCategories = $derived.by(() => {
	if (selectedCategory === "all") {
		return emojiCategories;
	}
	const found = emojiCategories.find((c) => c.id === selectedCategory);
	return found ? [found] : emojiCategories.length ? [emojiCategories[0]] : [];
});

$effect(() => {
	if (showEmojiPicker) {
		if (!emojiDataLoaded) {
			loadEmojiData().then((data) => {
				emojiCategories = data.categories;
				allEmojis = data.all;
				emojiDataLoaded = true;
			});
		}
		setTimeout(() => {
			emojiSearchInput?.focus();
		}, 60);
	} else {
		emojiSearchQuery = "";
		hoveredEmoji = null;
	}
});

function getPlayerInfo(msg: ChatMessage): {
	isPlayer: boolean;
	index: number;
	name: string;
	color: string;
} {
	const rawName = msg.username?.trim();
	if (!rawName && !msg.user_id) {
		return {
			isPlayer: false,
			index: -1,
			name: msg.chat_id === myChatId ? "You (Guest)" : "Spectator",
			color: "var(--color-text-muted)",
		};
	}

	const index = ordered_gameplayers.findIndex((p) => {
		if (msg.user_id && p.user.id === msg.user_id) return true;
		if (rawName && p.user.username.toLowerCase() === rawName.toLowerCase())
			return true;
		return false;
	});

	if (index !== -1) {
		const player = ordered_gameplayers[index];
		return {
			isPlayer: true,
			index,
			name: player.user.username,
			color: userColors[index % userColors.length],
		};
	}

	return {
		isPlayer: false,
		index: -1,
		name: rawName || (msg.chat_id === myChatId ? "You" : "Spectator"),
		color: "var(--color-text)",
	};
}

function formatTime(isoStr?: string): string {
	if (!isoStr) return "";
	try {
		const d = new Date(isoStr);
		return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
	} catch {
		return "";
	}
}

function isMine(msg: ChatMessage): boolean {
	// Current session: match by ephemeral chat_id
	if (myChatId && msg.chat_id === myChatId) return true;
	// History from a previous session: match by persistent user_id
	if (
		current_user?.id != null &&
		msg.user_id != null &&
		msg.user_id === current_user.id
	)
		return true;
	return false;
}

async function scrollToBottom() {
	await tick();
	if (messagesContainer) {
		messagesContainer.scrollTop = messagesContainer.scrollHeight;
	}
}

function connectWebSocket() {
	if (isDestroyed) return;

	const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
	const wsUrl = `${protocol}//${window.location.host}/ws/chat/${game_id}/`;

	connectionStatus = "connecting";

	try {
		socket = new WebSocket(wsUrl);

		socket.onopen = () => {
			connectionStatus = "connected";
			hasHistory = false;
		};

		socket.onmessage = (event) => {
			try {
				const data = JSON.parse(event.data) as ChatMessage;

				if (data.event === "chat_id") {
					myChatId = data.chat_id ?? null;
				} else if (data.event === "presence" && data.users) {
					onlineUsers = data.users;
				} else if (data.event === "message") {
					messages.push(data);
					if (!isOpen) {
						unreadCount += 1;
					} else {
						scrollToBottom();
					}
				} else if (data.event === "history" && data.messages) {
					// Prepend historical messages and mark that history has arrived.
					messages = [...data.messages, ...messages];
					if (isOpen) scrollToBottom();
				} else if (data.event === "connect") {
					if (
						data.chat_id &&
						!onlineUsers.some((u) => u.chat_id === data.chat_id)
					) {
						onlineUsers.push({
							chat_id: data.chat_id,
							username: data.username,
							user_id: data.user_id,
							is_game: data.is_game,
						});
					}
					if (data.username || (data.chat_id && data.chat_id !== myChatId)) {
						messages.push(data);
						if (isOpen) scrollToBottom();
					}
				} else if (data.event === "disconnect") {
					if (data.chat_id) {
						onlineUsers = onlineUsers.filter((u) => u.chat_id !== data.chat_id);
					}
					if (data.username || (data.chat_id && data.chat_id !== myChatId)) {
						messages.push(data);
						if (isOpen) scrollToBottom();
					}
				}
			} catch (e) {
				console.error("Error parsing chat message", e);
			}
		};

		socket.onclose = () => {
			connectionStatus = "disconnected";
			if (!isDestroyed) {
				reconnectTimer = setTimeout(connectWebSocket, 3000);
			}
		};

		socket.onerror = () => {
			connectionStatus = "disconnected";
			socket?.close();
		};
	} catch (e) {
		connectionStatus = "disconnected";
		reconnectTimer = setTimeout(connectWebSocket, 3000);
	}
}

function toggleDrawer() {
	isOpen = !isOpen;
}

function closeDrawer() {
	isOpen = false;
}

function handleKeydown(e: KeyboardEvent) {
	if (isOpen && e.key === "Escape") {
		closeDrawer();
	}
}

function sendMessage() {
	const text = inputText.trim();
	if (!text || !socket || socket.readyState !== WebSocket.OPEN) return;

	socket.send(JSON.stringify({ message: text }));
	inputText = "";
	showEmojiPicker = false;
	scrollToBottom();
	setTimeout(() => {
		inputElement?.focus();
	}, 50);
}

function handleInputKeydown(e: KeyboardEvent) {
	if (e.key === "Enter" && !e.shiftKey) {
		e.preventDefault();
		sendMessage();
	}
}

function insertEmoji(emoji: string) {
	if (inputElement) {
		const start = inputElement.selectionStart ?? inputText.length;
		const end = inputElement.selectionEnd ?? inputText.length;
		inputText = inputText.slice(0, start) + emoji + inputText.slice(end);
		const nextPos = start + emoji.length;
		setTimeout(() => {
			inputElement?.focus();
			inputElement?.setSelectionRange(nextPos, nextPos);
		}, 0);
	} else {
		inputText += emoji;
	}
}

const MIN_WIDTH = 300;
const DEFAULT_WIDTH = 380;
let drawerWidth = $state(DEFAULT_WIDTH);
let isResizing = $state(false);

function getMaxWidth(): number {
	if (typeof window === "undefined") return 800;
	return Math.min(800, Math.max(MIN_WIDTH + 100, window.innerWidth - 450));
}

function updateChatWidthVar(w: number) {
	document.documentElement.style.setProperty("--chat-width", `${w}px`);
}

function onResizePointerDown(e: PointerEvent) {
	if (window.innerWidth < 1280) return;
	e.preventDefault();
	isResizing = true;
	document.body.classList.add("game-chat-resizing");

	const startX = e.clientX;
	const startWidth = drawerWidth;
	const maxWidth = getMaxWidth();

	function onPointerMove(moveEvent: PointerEvent) {
		const deltaX = startX - moveEvent.clientX;
		const nextWidth = Math.min(
			maxWidth,
			Math.max(MIN_WIDTH, Math.round(startWidth + deltaX)),
		);
		drawerWidth = nextWidth;
		updateChatWidthVar(nextWidth);
	}

	function onPointerUp() {
		isResizing = false;
		document.body.classList.remove("game-chat-resizing");
		window.removeEventListener("pointermove", onPointerMove);
		window.removeEventListener("pointerup", onPointerUp);
		try {
			localStorage.setItem("game_chat_width", drawerWidth.toString());
		} catch {}
	}

	window.addEventListener("pointermove", onPointerMove);
	window.addEventListener("pointerup", onPointerUp);
}

function onResizeDoubleClick() {
	drawerWidth = DEFAULT_WIDTH;
	updateChatWidthVar(DEFAULT_WIDTH);
	try {
		localStorage.setItem("game_chat_width", DEFAULT_WIDTH.toString());
	} catch {}
}

function handleWindowResize() {
	if (window.innerWidth >= 1280) {
		const maxW = getMaxWidth();
		if (drawerWidth > maxW) {
			drawerWidth = maxW;
			updateChatWidthVar(maxW);
		}
	}
}

onMount(() => {
	try {
		const saved = localStorage.getItem("game_chat_width");
		if (saved) {
			const parsed = parseInt(saved, 10);
			if (!Number.isNaN(parsed)) {
				const maxW = getMaxWidth();
				drawerWidth = Math.min(maxW, Math.max(MIN_WIDTH, parsed));
			}
		}
	} catch {}
	updateChatWidthVar(drawerWidth);
	connectWebSocket();
});

onDestroy(() => {
	isDestroyed = true;
	document.body.classList.remove("game-chat-open");
	document.body.classList.remove("game-chat-resizing");
	if (reconnectTimer) clearTimeout(reconnectTimer);
	if (socket) {
		socket.close();
	}
});
</script>

<svelte:window onkeydown={handleKeydown} onresize={handleWindowResize} />


<!-- Backdrop overlay -->
{#if isOpen}
	<div
		class="game-chat-backdrop"
		onclick={closeDrawer}
		onkeydown={(e) => { if (e.key === "Escape") closeDrawer(); }}
		role="button"
		tabindex="0"
		aria-label="Close chat drawer"
	></div>
{/if}

<!-- Side Drawer -->
<aside
	class="game-chat-drawer"
	class:open={isOpen}
	style="--chat-panel-width: {drawerWidth}px;"
	aria-label="Game Chat"
>
	<!-- Drag resize handle (desktop only) -->
	<div
		class="chat-resize-handle"
		class:active={isResizing}
		onpointerdown={onResizePointerDown}
		ondblclick={onResizeDoubleClick}
		role="separator"
		aria-orientation="vertical"
		aria-valuenow={drawerWidth}
		aria-valuemin={MIN_WIDTH}
		aria-valuemax={getMaxWidth()}
		title="Drag to resize chat panel (Double-click to reset)"
	>
		<div class="resize-handle-bar"></div>
	</div>

	<!-- Drawer Header -->
	<div class="drawer-header">
		<div class="drawer-title-group">
			<div class="chat-header-icon">
				<i class="fas fa-gamepad"></i>
			</div>
			<div>
				<h3 class="drawer-title">Game Chat</h3>
				<div class="drawer-subtitle">
					<span
						class="status-indicator"
						class:online={connectionStatus === "connected"}
						class:pending={connectionStatus === "connecting"}
						class:offline={connectionStatus === "disconnected"}
					></span>
					<span class="status-text">
						{#if connectionStatus === "connected"}
							Live • Game #{game_id}
						{:else if connectionStatus === "connecting"}
							Connecting...
						{:else}
							Offline (reconnecting)
						{/if}
					</span>

					{#if connectionStatus === "connected"}
						<span class="subtitle-divider">•</span>
						<div
							class="online-badge"
							onmouseenter={() => (showOnlinePopover = true)}
							onmouseleave={() => (showOnlinePopover = false)}
							role="button"
							tabindex="0"
						>
							<i class="fas fa-users"></i>
							<span>{onlineCount} online</span>

							{#if showOnlinePopover}
								<div class="online-popover">
									<div class="online-popover-title">
										<i class="fas fa-circle online-bullet"></i>
										Online in chat ({onlineCount})
									</div>
									<div class="online-popover-users">
										{#each onlineUsersList as user}
											<div class="online-popover-user">
												<span class="user-bullet" style="background: {user.color}"></span>
												<span class="user-name" style="color: {user.color}">{user.displayName}</span>
												{#if user.isPlayer}
													<span class="player-badge" style="border-color: {user.color}; color: {user.color}">
														P{user.playerIndex + 1}
													</span>
												{/if}
												{#if user.is_game}
													<span class="game-badge">HOST</span>
												{/if}
											</div>
										{/each}
									</div>
								</div>
							{/if}
						</div>
					{/if}
				</div>
			</div>
		</div>

		<button type="button" class="drawer-close-btn" onclick={closeDrawer} aria-label="Close chat">
			<i class="fas fa-times"></i>
		</button>
	</div>

	<!-- Message Feed -->
	<div class="drawer-messages" bind:this={messagesContainer}>
		{#if messages.length === 0}
			<div class="chat-empty-state">
				<div class="empty-icon">
					<i class="fas fa-comment-dots"></i>
				</div>
				<h4>Live Match Chat</h4>
				<p>Chat with players and spectators in real time! Send cheer, banter, or emojis.</p>
			</div>
		{:else}
			{#each messages as msg, i}
				{#if msg.event === "connect"}
					<div class="system-message">
						<i class="fas fa-sign-in-alt"></i>
						<span>{msg.username || "Spectator"} joined the chat</span>
						{#if msg.datetime}
							<span class="system-time">{formatTime(msg.datetime)}</span>
						{/if}
					</div>
				{:else if msg.event === "disconnect"}
					<div class="system-message leave">
						<i class="fas fa-sign-out-alt"></i>
						<span>{msg.username || "Spectator"} left the chat</span>
						{#if msg.datetime}
							<span class="system-time">{formatTime(msg.datetime)}</span>
						{/if}
					</div>
				{:else if msg.event === "message"}
					{@const isMe = isMine(msg)}
					{@const playerInfo = getPlayerInfo(msg)}
					<div class="chat-message-row" class:mine={isMe}>
						<div class="message-bubble" class:mine={isMe}>
							<div class="message-header">
								<span class="message-sender" style="color: {playerInfo.color}">
									{playerInfo.name}
								</span>
								{#if playerInfo.isPlayer}
									<span class="player-badge" style="border-color: {playerInfo.color}; color: {playerInfo.color}">
										P{playerInfo.index + 1}
									</span>
								{/if}
								{#if msg.is_game}
									<span class="game-badge">HOST</span>
								{/if}
								{#if msg.datetime}
									<span class="message-time">{formatTime(msg.datetime)}</span>
								{/if}
							</div>
							<div class="message-text">{msg.message}</div>
						</div>
					</div>
				{/if}
			{/each}
		{/if}
	</div>

	<!-- Emoji Picker Popover -->
	{#if showEmojiPicker}
		<div class="emoji-picker-container">
			<div class="emoji-picker-top">
				<div class="emoji-search-bar">
					<i class="fas fa-search emoji-search-icon"></i>
					<input
						type="text"
						bind:this={emojiSearchInput}
						bind:value={emojiSearchQuery}
						placeholder="Search 1,900+ emojis..."
						class="emoji-search-input"
					/>
					{#if emojiSearchQuery}
						<button
							type="button"
							class="emoji-search-clear"
							onclick={() => (emojiSearchQuery = "")}
							aria-label="Clear search"
						>
							<i class="fas fa-times"></i>
						</button>
					{/if}
				</div>
				<button
					type="button"
					class="emoji-close-btn"
					onclick={() => (showEmojiPicker = false)}
					aria-label="Close emoji picker"
				>
					<i class="fas fa-times"></i>
				</button>
			</div>

			{#if !emojiSearchQuery.trim()}
				<div class="emoji-cat-nav">
					<button
						type="button"
						class="emoji-cat-tab"
						class:active={selectedCategory === "all"}
						onclick={() => (selectedCategory = "all")}
						title="All Emojis"
						aria-label="All Emojis"
					>
						<i class="fas fa-border-all"></i>
					</button>
					{#each emojiCategories as cat (cat.id)}
						<button
							type="button"
							class="emoji-cat-tab"
							class:active={selectedCategory === cat.id}
							onclick={() => (selectedCategory = cat.id)}
							title={cat.name}
							aria-label={cat.name}
						>
							<i class={cat.icon}></i>
						</button>
					{/each}
				</div>
			{/if}

			<div class="emoji-picker-body">
				{#if emojiSearchQuery.trim()}
					<div class="emoji-cat-title">
						{#if searchResults.length > 0}
							Found {searchResults.length}{searchResults.length >= 140 ? "+" : ""} emojis
						{:else}
							No emojis matching "{emojiSearchQuery}"
						{/if}
					</div>
					<div class="emoji-grid">
						{#each searchResults as item (item.e)}
							<button
								type="button"
								class="emoji-btn"
								onclick={() => insertEmoji(item.e)}
								onmouseenter={() => (hoveredEmoji = item)}
								onmouseleave={() => (hoveredEmoji = null)}
								title={item.n}
							>
								{item.e}
							</button>
						{/each}
					</div>
				{:else}
					{#each currentDisplayCategories as cat (cat.id)}
						<div class="emoji-cat-title">
							{cat.name} <span class="emoji-cat-count">({cat.emojis.length})</span>
						</div>
						<div class="emoji-grid">
							{#each cat.emojis as item (item.e)}
								<button
									type="button"
									class="emoji-btn"
									onclick={() => insertEmoji(item.e)}
									onmouseenter={() => (hoveredEmoji = item)}
									onmouseleave={() => (hoveredEmoji = null)}
									title={item.n}
								>
									{item.e}
								</button>
							{/each}
						</div>
					{/each}
				{/if}
			</div>

			<div class="emoji-picker-preview">
				{#if hoveredEmoji}
					<span class="preview-emoji">{hoveredEmoji.e}</span>
					<span class="preview-name">{hoveredEmoji.n}</span>
				{:else}
					<span class="preview-tip">Click to insert • Search by keyword</span>
				{/if}
			</div>
		</div>
	{/if}

	<!-- Drawer Input Area -->
	<div class="drawer-footer">
		<div class="chat-input-wrapper">
			<button
				type="button"
				class="chat-action-btn emoji-toggle-btn"
				class:active={showEmojiPicker}
				onclick={() => (showEmojiPicker = !showEmojiPicker)}
				title="Add Emoji"
				aria-label="Toggle emoji picker"
			>
				<i class="far fa-smile"></i>
			</button>

			<input
				type="text"
				bind:this={inputElement}
				bind:value={inputText}
				onkeydown={handleInputKeydown}
				placeholder="Type a message..."
				class="chat-text-input"
				maxlength={500}
				disabled={connectionStatus === "disconnected"}
			/>

			<button
				type="button"
				class="chat-send-btn"
				disabled={!inputText.trim() || connectionStatus !== "connected"}
				onclick={sendMessage}
				title="Send message (Enter)"
				aria-label="Send message"
			>
				<i class="fas fa-paper-plane"></i>
			</button>
		</div>
	</div>
</aside>

<style>
	/* Backdrop - Overlay mode only */
	.game-chat-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.55);
		backdrop-filter: blur(4px);
		z-index: 1050;
		cursor: pointer;
		animation: fade-in 0.25s ease forwards;
	}

	@keyframes fade-in {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}

	/* Drawer / Side Panel */
	.game-chat-drawer {
		position: fixed;
		top: 0;
		right: 0;
		bottom: 0;
		width: var(--chat-panel-width, var(--chat-width, 380px));
		background: #1c1c1f;
		border-left: 1px solid rgba(255, 255, 255, 0.12);
		display: flex;
		flex-direction: column;
		z-index: 1060;
		transform: translateX(100%);
		transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
	}

	.game-chat-drawer.open {
		transform: translateX(0);
	}

	/* Header */
	.drawer-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 1.1rem 1.25rem;
		background: #232326;
		border-bottom: 1px solid rgba(255, 255, 255, 0.08);
	}

	.drawer-title-group {
		display: flex;
		align-items: center;
		gap: 0.85rem;
	}

	.chat-header-icon {
		width: 40px;
		height: 40px;
		border-radius: 10px;
		background: rgba(165, 56, 59, 0.18);
		border: 1px solid rgba(165, 56, 59, 0.4);
		display: flex;
		align-items: center;
		justify-content: center;
		color: #e55356;
		font-size: 1.15rem;
	}

	.drawer-title {
		margin: 0;
		font-size: 1.15rem;
		font-weight: 700;
		color: #ffffff;
		letter-spacing: -0.01em;
	}

	.drawer-subtitle {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		font-size: 0.78rem;
		color: var(--color-text-muted);
		margin-top: 0.15rem;
	}

	.status-indicator {
		width: 8px;
		height: 8px;
		border-radius: 50%;
	}

	.status-indicator.online {
		background: #10b981;
	}

	.status-indicator.pending {
		background: #f59e0b;
	}

	.status-indicator.offline {
		background: #ef4444;
	}

	.drawer-close-btn {
		width: 36px;
		height: 36px;
		border-radius: 8px;
		background: transparent;
		border: 1px solid transparent;
		color: var(--color-text-muted);
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 1.1rem;
		cursor: pointer;
		transition: background 0.15s ease, color 0.15s ease;
	}

	.drawer-close-btn:hover {
		background: rgba(255, 255, 255, 0.08);
		color: #ffffff;
	}

	.subtitle-divider {
		color: rgba(255, 255, 255, 0.2);
	}

	.online-badge {
		position: relative;
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		padding: 2px 7px;
		border-radius: 10px;
		background: rgba(255, 255, 255, 0.07);
		border: 1px solid rgba(255, 255, 255, 0.1);
		color: #e4e4e7;
		font-weight: 600;
		font-size: 0.72rem;
		cursor: pointer;
		transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
	}

	.online-badge:hover {
		background: rgba(255, 255, 255, 0.12);
		border-color: rgba(255, 255, 255, 0.2);
		color: #ffffff;
	}

	.online-badge i {
		font-size: 0.68rem;
		color: #10b981;
	}

	.online-popover {
		position: absolute;
		top: calc(100% + 8px);
		right: 0;
		left: auto;
		width: 220px;
		max-width: calc(100vw - 32px);
		background: #242428;
		border: 1px solid var(--color-border-2);
		border-radius: 8px;
		z-index: 1070;
		padding: 0.6rem;
		pointer-events: auto;
		animation: popover-fade 0.15s ease forwards;
	}

	@keyframes popover-fade {
		from {
			opacity: 0;
			transform: translateY(-4px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.online-popover-title {
		font-size: 0.7rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: var(--color-text-muted);
		padding-bottom: 0.4rem;
		margin-bottom: 0.4rem;
		border-bottom: 1px solid rgba(255, 255, 255, 0.08);
		display: flex;
		align-items: center;
		gap: 0.35rem;
	}

	.online-bullet {
		font-size: 0.5rem;
		color: #10b981;
	}

	.online-popover-users {
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
		max-height: 180px;
		overflow-y: auto;
	}

	.online-popover-user {
		display: flex;
		align-items: center;
		gap: 0.45rem;
		font-size: 0.78rem;
	}

	.user-bullet {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.user-name {
		font-weight: 600;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	/* Message Feed */
	.drawer-messages {
		flex: 1;
		overflow-y: auto;
		padding: 1.25rem;
		display: flex;
		flex-direction: column;
		gap: 0.85rem;
		background: #17171a;
	}

	.chat-empty-state {
		margin: auto;
		text-align: center;
		padding: 2rem 1.5rem;
		color: var(--color-text-muted);
	}

	.chat-empty-state .empty-icon {
		font-size: 2.8rem;
		color: rgba(255, 255, 255, 0.12);
		margin-bottom: 1rem;
	}

	.chat-empty-state h4 {
		font-size: 1.05rem;
		color: #ffffff;
		margin-bottom: 0.4rem;
		font-weight: 600;
	}

	.chat-empty-state p {
		font-size: 0.82rem;
		line-height: 1.45;
		max-width: 260px;
		margin: 0 auto;
	}

	/* System message */
	.system-message {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.4rem;
		font-size: 0.72rem;
		color: #71717a;
		padding: 0.25rem 0.5rem;
		background: rgba(255, 255, 255, 0.02);
		border-radius: 6px;
		text-align: center;
	}

	.system-message i {
		font-size: 0.65rem;
		color: #10b981;
	}

	.system-message.leave i {
		color: #ef4444;
	}

	.system-time {
		color: #52525b;
		margin-left: 0.2rem;
	}

	/* Message Bubbles */
	.chat-message-row {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		max-width: 88%;
	}

	.chat-message-row.mine {
		align-self: flex-end;
		align-items: flex-end;
	}

	.message-bubble {
		padding: 0.65rem 0.9rem;
		border-radius: 12px;
		background: #242428;
		word-break: break-word;
	}

	.message-bubble.mine {
		background: rgba(165, 56, 59, 0.28);
	}

	.message-header {
		display: flex;
		align-items: center;
		gap: 0.45rem;
		margin-bottom: 0.25rem;
		font-size: 0.76rem;
	}

	.message-sender {
		font-weight: 700;
		letter-spacing: 0.01em;
	}

	.player-badge {
		font-size: 0.62rem;
		font-weight: 800;
		padding: 1px 4px;
		border-radius: 4px;
		border: 1px solid currentColor;
		line-height: 1;
	}

	.game-badge {
		font-size: 0.62rem;
		font-weight: 800;
		padding: 1px 5px;
		border-radius: 4px;
		background: #3b82f6;
		color: #ffffff;
		line-height: 1;
	}

	.message-time {
		color: #71717a;
		font-size: 0.68rem;
		margin-left: auto;
	}

	.message-text {
		font-size: 0.88rem;
		line-height: 1.45;
		color: #f4f4f5;
		white-space: pre-wrap;
		font-family: var(--font-sans);
	}

	/* Emoji Picker Popover */
	.emoji-picker-container {
		background: #202024;
		border-top: 1px solid rgba(255, 255, 255, 0.1);
		height: 320px;
		max-height: 320px;
		display: flex;
		flex-direction: column;
		animation: slide-up 0.2s cubic-bezier(0.16, 1, 0.3, 1);
	}

	@keyframes slide-up {
		from {
			opacity: 0;
			transform: translateY(12px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.emoji-picker-top {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.55rem 0.75rem;
		border-bottom: 1px solid rgba(255, 255, 255, 0.08);
		background: #242428;
	}

	.emoji-search-bar {
		flex: 1;
		display: flex;
		align-items: center;
		gap: 0.45rem;
		background: #18181b;
		border: 1px solid rgba(255, 255, 255, 0.12);
		border-radius: 20px;
		padding: 0.28rem 0.65rem;
		transition: border-color 0.15s ease, box-shadow 0.15s ease;
	}

	.emoji-search-bar:focus-within {
		border-color: #c93b3e;
		box-shadow: 0 0 0 2px rgba(201, 59, 62, 0.25);
	}

	.emoji-search-icon {
		color: #71717a;
		font-size: 0.75rem;
	}

	.emoji-search-input {
		flex: 1;
		background: transparent;
		border: none;
		outline: none;
		color: #ffffff;
		font-size: 0.82rem;
		min-width: 0;
	}

	.emoji-search-input::placeholder {
		color: #71717a;
	}

	.emoji-search-clear {
		background: transparent;
		border: none;
		color: #71717a;
		cursor: pointer;
		font-size: 0.75rem;
		padding: 0 2px;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.emoji-search-clear:hover {
		color: #ffffff;
	}

	.emoji-close-btn {
		background: transparent;
		border: none;
		color: #a1a1aa;
		cursor: pointer;
		font-size: 0.85rem;
		padding: 4px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 4px;
		transition: color 0.15s ease, background 0.15s ease;
	}

	.emoji-close-btn:hover {
		color: #ffffff;
		background: rgba(255, 255, 255, 0.08);
	}

	/* Category Navigation Tabs */
	.emoji-cat-nav {
		display: flex;
		align-items: center;
		gap: 0.2rem;
		padding: 0.35rem 0.6rem;
		background: #1c1c1f;
		border-bottom: 1px solid rgba(255, 255, 255, 0.06);
		overflow-x: auto;
		scrollbar-width: none;
	}

	.emoji-cat-nav::-webkit-scrollbar {
		display: none;
	}

	.emoji-cat-tab {
		background: transparent;
		border: 1px solid transparent;
		color: #71717a;
		width: 28px;
		height: 28px;
		border-radius: 6px;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 0.85rem;
		cursor: pointer;
		transition: all 0.15s ease;
		flex-shrink: 0;
	}

	.emoji-cat-tab:hover {
		color: #ffffff;
		background: rgba(255, 255, 255, 0.08);
	}

	.emoji-cat-tab.active {
		color: #ffffff;
		background: rgba(201, 59, 62, 0.35);
		border-color: rgba(201, 59, 62, 0.6);
	}

	.emoji-picker-body {
		flex: 1;
		overflow-y: auto;
		padding: 0.5rem 0.75rem;
		scrollbar-width: thin;
		scrollbar-color: #3f3f46 transparent;
	}

	.emoji-picker-body::-webkit-scrollbar {
		width: 6px;
	}

	.emoji-picker-body::-webkit-scrollbar-thumb {
		background: #3f3f46;
		border-radius: 3px;
	}

	.emoji-cat-title {
		font-size: 0.68rem;
		text-transform: uppercase;
		font-weight: 700;
		color: #71717a;
		margin: 0.4rem 0 0.35rem 0;
		letter-spacing: 0.05em;
		display: flex;
		align-items: center;
		gap: 0.35rem;
	}

	.emoji-cat-count {
		font-size: 0.65rem;
		color: #52525b;
		font-weight: 500;
	}

	.emoji-grid {
		display: grid;
		grid-template-columns: repeat(8, 1fr);
		gap: 0.2rem;
		margin-bottom: 0.6rem;
	}

	.emoji-btn {
		background: transparent;
		border: 1px solid transparent;
		border-radius: 6px;
		font-size: 1.35rem;
		font-family: var(--font-emoji);
		padding: 0.2rem;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: background 0.12s ease, transform 0.1s ease;
		line-height: 1;
	}

	.emoji-btn:hover {
		background: rgba(255, 255, 255, 0.12);
		transform: scale(1.22);
	}

	/* Preview bar */
	.emoji-picker-preview {
		padding: 0.35rem 0.75rem;
		background: #18181b;
		border-top: 1px solid rgba(255, 255, 255, 0.06);
		display: flex;
		align-items: center;
		gap: 0.5rem;
		min-height: 32px;
		font-size: 0.75rem;
		color: #a1a1aa;
	}

	.preview-emoji {
		font-family: var(--font-emoji);
		font-size: 1.15rem;
		line-height: 1;
	}

	.preview-name {
		text-transform: capitalize;
		color: #f4f4f5;
		font-weight: 600;
	}

	.preview-tip {
		color: #52525b;
		font-size: 0.7rem;
	}

	/* Footer Input */
	.drawer-footer {
		padding: 0.85rem 1rem;
		background: #202024;
		border-top: 1px solid rgba(255, 255, 255, 0.08);
	}

	.chat-input-wrapper {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		background: #141416;
		border: 1px solid rgba(255, 255, 255, 0.12);
		border-radius: 24px;
		padding: 0.35rem 0.5rem 0.35rem 0.75rem;
		transition: border-color 0.2s ease, box-shadow 0.2s ease;
	}

	.chat-input-wrapper:focus-within {
		border-color: #c93b3e;
		box-shadow: 0 0 0 3px rgba(201, 59, 62, 0.25);
	}

	.chat-action-btn {
		background: transparent;
		border: none;
		color: #a1a1aa;
		font-size: 1.15rem;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 0.25rem;
		border-radius: 50%;
		transition: color 0.15s ease, transform 0.15s ease;
	}

	.chat-action-btn:hover {
		color: #ffffff;
		transform: scale(1.1);
	}

	.chat-action-btn.active {
		color: #e55356;
	}

	.chat-text-input {
		flex: 1;
		background: transparent;
		border: none;
		outline: none;
		color: #ffffff;
		font-size: 0.88rem;
		padding: 0.3rem 0;
		font-family: var(--font-sans);
	}

	.chat-text-input::placeholder {
		color: #52525b;
	}

	.chat-send-btn {
		width: 34px;
		height: 34px;
		border-radius: 50%;
		background: #c93b3e;
		border: none;
		color: #ffffff;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 0.9rem;
		cursor: pointer;
		transition: background 0.15s ease, transform 0.15s ease;
		outline: none;
	}

	.chat-send-btn:hover:not(:disabled) {
		background: #e55356;
		transform: scale(1.06);
	}

	.chat-send-btn:disabled {
		background: #2e2e32;
		color: #52525b;
		cursor: not-allowed;
	}

	/* Chat Resize Handle (desktop only) */
	.chat-resize-handle {
		display: none;
	}

	/* Desktop: side panel mode when there is room (>= 1280px) */
	@media (min-width: 1280px) {
		:global(body.game-chat-open) {
			overflow: hidden !important;
			height: 100vh !important;
		}

		:global(body.game-chat-open .site-main-layout) {
			width: calc(100vw - var(--chat-width, 380px)) !important;
			max-width: calc(100vw - var(--chat-width, 380px)) !important;
			height: 100vh !important;
			overflow-y: auto !important;
			overflow-x: hidden !important;
		}

		:global(.site-main-layout) {
			transition: width 0.25s cubic-bezier(0.16, 1, 0.3, 1);
			scrollbar-width: thin;
			scrollbar-color: #3f3f46 var(--color-bg);
		}

		/* Disable transitions and text-selection during drag */
		:global(body.game-chat-resizing) {
			cursor: col-resize !important;
			user-select: none !important;
		}

		:global(body.game-chat-resizing .site-main-layout),
		:global(body.game-chat-resizing .game-chat-drawer) {
			transition: none !important;
			user-select: none !important;
		}

		:global(.site-main-layout::-webkit-scrollbar) {
			width: 8px;
		}

		:global(.site-main-layout::-webkit-scrollbar-track) {
			background: var(--color-bg);
		}

		:global(.site-main-layout::-webkit-scrollbar-thumb) {
			background: #3f3f46;
			border-radius: 4px;
		}

		:global(.site-main-layout::-webkit-scrollbar-thumb:hover) {
			background: #52525b;
		}

		.game-chat-backdrop {
			display: none !important;
		}

		.game-chat-drawer {
			width: var(--chat-panel-width, var(--chat-width, 380px));
			box-shadow: none;
			border-left: 1px solid var(--color-border);
			z-index: 1020;
		}

		.chat-resize-handle {
			display: block;
			position: absolute;
			top: 0;
			bottom: 0;
			left: -5px;
			width: 10px;
			cursor: col-resize;
			z-index: 20;
			touch-action: none;
		}

		.resize-handle-bar {
			position: absolute;
			top: 0;
			bottom: 0;
			left: 4px;
			width: 2px;
			background: transparent;
			transition: background 0.15s ease;
		}

		.chat-resize-handle:hover .resize-handle-bar,
		.chat-resize-handle.active .resize-handle-bar {
			background: #c93b3e;
			box-shadow: 0 0 6px rgba(201, 59, 62, 0.6);
		}
	}

	/* Mobile & Tablet: full screen overlay mode (< 1280px) */
	@media (max-width: 1279.98px) {
		:global(body.game-chat-open) {
			overflow: hidden !important;
			height: 100vh !important;
		}

		.game-chat-backdrop {
			display: none !important;
		}

		.game-chat-drawer {
			top: 0 !important;
			left: 0 !important;
			right: 0 !important;
			bottom: 0 !important;
			width: 100vw !important;
			max-width: 100vw !important;
			height: 100% !important;
			height: 100dvh !important;
			border-radius: 0 !important;
			border: none !important;
			box-shadow: none !important;
			z-index: 1060;
		}

		.drawer-header {
			padding: 0.85rem 1rem;
		}

		.drawer-footer {
			padding-bottom: max(0.85rem, env(safe-area-inset-bottom, 0.85rem));
		}
	}

</style>
