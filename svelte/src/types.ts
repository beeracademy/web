export interface CardData {
  value: number;
  suit: string;
  start_delta_ms: number;

  chug_id: number | null;
  chug_duration_ms: number | null;
  chug_start_start_delta_ms: number | null;
}

export interface PlayerStatsData {
  id: number;
  username: string;

  total_sips: number;
  full_beers: number;
  extra_sips: number;

  total_time: number;
  sips_per_turn: number;
  time_per_sip: number;
  time_per_turn: number;
}

export interface Location {
  latitude: number;
  longitude: number;
  accuracy: number;
}

export interface GameData {
  id: number;
  dnf: boolean;
  has_ended: boolean;
  official: boolean;
  sips_per_beer: number;

  cards: CardData[];
  player_stats: PlayerStatsData[];

  start_datetime: string | null;
  end_datetime: string | null;

  description: string | null;
  description_html: string | null;

  playerCount: number;

  image: string | null;
  location: Location | null;
}

export interface UserData {
  id: number;
  username: string;
  image_url: string;
}

export interface GamePlayerData {
  dnf: boolean;
  user: UserData;
}

export interface ChugData {
  card: CardData;
  gameplayer: GamePlayerData;
}
