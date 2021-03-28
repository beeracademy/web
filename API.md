# Game API

## Create user

### Request

```javascript
// POST /api/users/
{
  "username": string,
  "password": string,
}
```

### Response

```javascript
{
  "id": int,
  ...
}
```

## Authenticate

### Request

```javascript
// POST /api-token-auth/`
{
  "username": string,
  "password": string,
}
```

### Response

On success:

```javascript
{
  "id": int,
  "token": string,
  "image": string, // relative path from web server to image url
}
```

If a user with that username doesn't exist, the response is 404 Not Found.

If a user with that username exists, but the password was wrong, the response is 400 Bad Request.

## Start game

### Request

```javascript
// POST /api/games/
{
  "tokens": string[],
}
```

### Response

```javascript
{
  "id": int,
  "token": string,
  "shuffle_indices": int[],
  "start_datetime": datetime_string,
  ...
}
```

## Update game

### Request

```javascript
// POST /api/games/<game_id>/update_state/
// Authorization: GameToken <game_token>
{
  "official": bool,
  "cards": card[], // see below
  "has_ended": bool,
  "description": string, // only at end of game
  "dnf": bool,
}
```

`card` type definition:

```javascript
{
  "value": int,
  "suit": string,
  "start_delta_ms": int,

  // Should only be given if value == 14 and
  // player has started chugging:
  "chug_start_start_delta_ms": int,

  // Should only be given if value == 14 and
  // player has finished chugging:
  "chug_end_start_delta_ms": int,
}
```

### Response

```javascript
{
}
```

## Resume game

### Request

```javascript
// POST /api/games/<game_id>/resume/
// Authorization: Token <user_token>
{
}
```

### Response

```javascript
{
  "token": string,
  ...
}

## Update game image

### Request
```

// POST /api/games/<game_id>/update_image/
// Authorization: GameToken <game_token>
// multipart/form-data with image field containing image

````

### Response
```javascript
{}
````

## Delete game image

### Request

```
// POST /api/games/<game_id>/delete_image/
// Authorization: GameToken <game_token>
```

### Response

```javascript
{
}
```

## Get list of ranked users for face cards

### Request

```javascript
// GET /api/ranked_cards/
{
}
```

### Response

```javascript
{
  "{suit}-{value}": { // example: S-12
    "user_id": int,
    "user_username": string,
    "user_image": string,
    "ranking_name": string,
    "ranking_value": string,
  },
}
```

# Player stats

## Get stats for a user

### Request

```javascript
// GET /api/stats/<user_id>/
{
}
```

### Response

```javascript
[
    {
        "season_number": int,
        "total_games": int,
        "total_time_played_seconds": float,
        "total_sips": int,
        "best_game": int,
        "worst_game": int,
        "best_game_sips": int?,
        "worst_game_sips": int?,
        "total_chugs": int,
        "fastest_chug": int?,
        "fastest_chug_duration_ms": int?,
        "average_chug_time_seconds": float?,
    },
    ...
]
```
