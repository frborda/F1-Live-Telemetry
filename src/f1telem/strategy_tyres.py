"""Vida de gomas por compuesto y circuito (2022-2026), minada de
los stints REALES de Fast-F1 (tools/tyre_life_miner.py):
{compuesto: [mediana, P90, n_stints]} en vueltas de TyreLife.
GLOBAL es el fallback para circuitos sin historia."""

TYRE_LIFE = {
 "Abu Dhabi Grand Prix": {
  "HARD": [
   25.0,
   43,
   106
  ],
  "MEDIUM": [
   16.5,
   26,
   88
  ],
  "SOFT": [
   8,
   25,
   9
  ],
  "track_length": 5215.6
 },
 "Australian Grand Prix": {
  "HARD": [
   24,
   47,
   117
  ],
  "MEDIUM": [
   12.0,
   23,
   76
  ],
  "SOFT": [
   5.0,
   11,
   56
  ],
  "track_length": 5226.1
 },
 "Austrian Grand Prix": {
  "HARD": [
   26.0,
   32,
   124
  ],
  "MEDIUM": [
   19.0,
   28,
   164
  ],
  "SOFT": [
   14.5,
   21,
   18
  ],
  "track_length": 4291.3
 },
 "Azerbaijan Grand Prix": {
  "HARD": [
   33.0,
   43,
   88
  ],
  "MEDIUM": [
   13,
   23,
   77
  ],
  "SOFT": [
   1.5,
   15,
   8
  ],
  "track_length": 5934.2
 },
 "Bahrain Grand Prix": {
  "HARD": [
   20.0,
   27,
   92
  ],
  "MEDIUM": [
   17.0,
   25,
   50
  ],
  "SOFT": [
   15,
   20,
   131
  ],
  "track_length": 5358.7
 },
 "Barcelona Grand Prix": {
  "HARD": [
   22.0,
   30,
   38
  ],
  "MEDIUM": [
   14,
   24,
   19
  ],
  "SOFT": [
   12.5,
   15,
   12
  ],
  "track_length": 4628.7
 },
 "Belgian Grand Prix": {
  "HARD": [
   19,
   29,
   67
  ],
  "MEDIUM": [
   15,
   32,
   125
  ],
  "SOFT": [
   13.0,
   23,
   48
  ],
  "track_length": 6933.3
 },
 "British Grand Prix": {
  "HARD": [
   18.5,
   27,
   50
  ],
  "MEDIUM": [
   19,
   32,
   119
  ],
  "SOFT": [
   13.0,
   22,
   78
  ],
  "track_length": 5818.5
 },
 "Canadian Grand Prix": {
  "HARD": [
   30.0,
   51,
   118
  ],
  "MEDIUM": [
   16.0,
   36,
   120
  ],
  "SOFT": [
   13.5,
   35,
   38
  ],
  "track_length": 4315.7
 },
 "Chinese Grand Prix": {
  "HARD": [
   33.0,
   46,
   70
  ],
  "MEDIUM": [
   12,
   20,
   63
  ],
  "SOFT": [
   9,
   20,
   9
  ],
  "track_length": 5385.4
 },
 "Dutch Grand Prix": {
  "HARD": [
   30,
   45,
   61
  ],
  "MEDIUM": [
   23.0,
   30,
   74
  ],
  "SOFT": [
   16.0,
   30,
   118
  ],
  "track_length": 4227.7
 },
 "Emilia Romagna Grand Prix": {
  "HARD": [
   29,
   41,
   55
  ],
  "MEDIUM": [
   26,
   45,
   65
  ],
  "SOFT": [
   9.0,
   13,
   8
  ],
  "track_length": 4868.2
 },
 "French Grand Prix": {
  "HARD": [
   35,
   36,
   23
  ],
  "MEDIUM": [
   18.0,
   21,
   22
  ],
  "track_length": 5750.4
 },
 "GLOBAL": {
  "HARD": [
   26,
   42,
   1939
  ],
  "MEDIUM": [
   18,
   32,
   2213
  ],
  "SOFT": [
   14,
   26,
   1113
  ]
 },
 "Hungarian Grand Prix": {
  "HARD": [
   29,
   40,
   91
  ],
  "MEDIUM": [
   22.0,
   32,
   100
  ],
  "SOFT": [
   16.5,
   23,
   36
  ],
  "track_length": 4336.1
 },
 "Italian Grand Prix": {
  "HARD": [
   27.0,
   39,
   76
  ],
  "MEDIUM": [
   19,
   33,
   77
  ],
  "SOFT": [
   9,
   20,
   27
  ],
  "track_length": 5743.2
 },
 "Japanese Grand Prix": {
  "HARD": [
   22.0,
   33,
   94
  ],
  "MEDIUM": [
   18,
   24,
   97
  ],
  "SOFT": [
   6.0,
   18,
   38
  ],
  "track_length": 5770.2
 },
 "Las Vegas Grand Prix": {
  "HARD": [
   24.0,
   33,
   86
  ],
  "MEDIUM": [
   13,
   24,
   61
  ],
  "SOFT": [
   5.0,
   10,
   6
  ],
  "track_length": 6137.9
 },
 "Mexico City Grand Prix": {
  "HARD": [
   37,
   45,
   57
  ],
  "MEDIUM": [
   30,
   42,
   83
  ],
  "SOFT": [
   27,
   35,
   49
  ],
  "track_length": 4234.9
 },
 "Miami Grand Prix": {
  "HARD": [
   30,
   43,
   93
  ],
  "MEDIUM": [
   20,
   29,
   109
  ],
  "SOFT": [
   15,
   19,
   13
  ],
  "track_length": 5335.2
 },
 "Monaco Grand Prix": {
  "HARD": [
   31,
   62,
   105
  ],
  "MEDIUM": [
   21.0,
   53,
   96
  ],
  "SOFT": [
   9.5,
   24,
   70
  ],
  "track_length": 3278.9
 },
 "Qatar Grand Prix": {
  "HARD": [
   13,
   25,
   91
  ],
  "MEDIUM": [
   19,
   35,
   107
  ],
  "SOFT": [
   6.0,
   20,
   16
  ],
  "track_length": 5374.6
 },
 "Saudi Arabian Grand Prix": {
  "HARD": [
   34.0,
   43,
   72
  ],
  "MEDIUM": [
   16.0,
   31,
   78
  ],
  "SOFT": [
   14,
   19,
   9
  ],
  "track_length": 6095.7
 },
 "Singapore Grand Prix": {
  "HARD": [
   34,
   43,
   49
  ],
  "MEDIUM": [
   24,
   36,
   71
  ],
  "SOFT": [
   18.0,
   30,
   30
  ],
  "track_length": 4873.9
 },
 "Spanish Grand Prix": {
  "HARD": [
   27,
   35,
   37
  ],
  "MEDIUM": [
   22.5,
   28,
   84
  ],
  "SOFT": [
   17.0,
   24,
   150
  ],
  "track_length": 4623.6
 },
 "S\u00e3o Paulo Grand Prix": {
  "HARD": [
   10.0,
   29,
   8
  ],
  "MEDIUM": [
   23.0,
   34,
   86
  ],
  "SOFT": [
   19,
   28,
   113
  ],
  "track_length": 4237.0
 },
 "United States Grand Prix": {
  "HARD": [
   22,
   36,
   71
  ],
  "MEDIUM": [
   19.0,
   31,
   102
  ],
  "SOFT": [
   26,
   29,
   23
  ],
  "track_length": 5436.0
 }
}
