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
  "start_datetime": datetime_string,
  ...
}
```

## Update game

### Request
```javascript
// POST /api/games/<game_id>/update_state/
{
  "start_datetime": datetime_string,
  "official": bool,
  "seed": int[],
  "cards": card[],               // see below
  "end_datime": datetime_string, // only at end of game
  "description": string,         // only at end of game
}
```

`card` type definition:
```javascript
{
  "value": int,
  "suit": string,
  "drawn_datetime": datetime_string,

  // Should only be given if value == 14 and
  // player has finished chugging:
  "chug_duration_ms": int,
}
```

### Response
```javascript
{}
```
