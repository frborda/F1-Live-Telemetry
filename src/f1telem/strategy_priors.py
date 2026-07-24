"""Priors de estrategia por circuito, generados del backtest de
las carreras cosechadas 2022-2026 (harvest + backtest2.py).
Clave = nombre del meeting; track_length valida que el circuito
sea el mismo (p.ej. Spanish GP Barcelona vs Madrid 2026)."""

PRIORS = {
 "Abu Dhabi Grand Prix": {
  "gain": [
   3.24,
   4,
   119
  ],
  "pit_loss": [
   24.1,
   4,
   122
  ],
  "races": 4,
  "track_length": 5215.6
 },
 "Australian Grand Prix": {
  "gain": [
   1.9,
   3,
   71
  ],
  "pit_loss": [
   22.76,
   5,
   108
  ],
  "races": 5,
  "sc": [
   0.68,
   3,
   39
  ],
  "track_length": 5226.1,
  "vsc": [
   0.75,
   3,
   26
  ]
 },
 "Austrian Grand Prix": {
  "gain": [
   3.06,
   5,
   182
  ],
  "pit_loss": [
   22.73,
   5,
   179
  ],
  "races": 5,
  "sc": [
   0.28,
   2,
   3
  ],
  "track_length": 4291.3,
  "vsc": [
   0.75,
   3,
   21
  ]
 },
 "Azerbaijan Grand Prix": {
  "gain": [
   2.18,
   3,
   56
  ],
  "pit_loss": [
   21.7,
   4,
   59
  ],
  "races": 4,
  "sc": [
   0.78,
   2,
   12
  ],
  "track_length": 5934.2,
  "vsc": [
   0.71,
   1,
   17
  ]
 },
 "Bahrain Grand Prix": {
  "gain": [
   4.33,
   4,
   153
  ],
  "pit_loss": [
   24.89,
   4,
   161
  ],
  "races": 4,
  "sc": [
   0.84,
   2,
   25
  ],
  "track_length": 5358.7,
  "vsc": [
   0.93,
   1,
   6
  ]
 },
 "Barcelona Grand Prix": {
  "gain": [
   5.18,
   1,
   42
  ],
  "pit_loss": [
   24.4,
   1,
   42
  ],
  "races": 1,
  "track_length": 4628.7,
  "vsc": [
   0.82,
   1,
   6
  ]
 },
 "Belgian Grand Prix": {
  "gain": [
   3.87,
   5,
   128
  ],
  "pit_loss": [
   19.45,
   5,
   146
  ],
  "races": 5,
  "sc": [
   0.75,
   2,
   8
  ],
  "track_length": 6933.3,
  "vsc": [
   0.88,
   1,
   9
  ]
 },
 "British Grand Prix": {
  "gain": [
   3.52,
   5,
   64
  ],
  "pit_loss": [
   25.45,
   5,
   152
  ],
  "races": 5,
  "sc": [
   0.73,
   4,
   39
  ],
  "track_length": 5818.5,
  "vsc": [
   0.8,
   3,
   11
  ]
 },
 "Canadian Grand Prix": {
  "gain": [
   2.61,
   4,
   80
  ],
  "pit_loss": [
   19.84,
   5,
   104
  ],
  "races": 5,
  "sc": [
   0.72,
   4,
   53
  ],
  "track_length": 4315.7,
  "vsc": [
   0.79,
   2,
   28
  ]
 },
 "Chinese Grand Prix": {
  "gain": [
   4.35,
   3,
   49
  ],
  "pit_loss": [
   23.57,
   3,
   57
  ],
  "races": 3,
  "sc": [
   0.86,
   2,
   23
  ],
  "track_length": 5385.4,
  "vsc": [
   0.78,
   1,
   4
  ]
 },
 "Dutch Grand Prix": {
  "gain": [
   3.5,
   4,
   79
  ],
  "pit_loss": [
   22.43,
   4,
   148
  ],
  "races": 4,
  "sc": [
   0.84,
   3,
   50
  ],
  "track_length": 4227.7,
  "vsc": [
   0.9,
   2,
   11
  ]
 },
 "Emilia Romagna Grand Prix": {
  "gain": [
   2.92,
   3,
   73
  ],
  "pit_loss": [
   29.18,
   3,
   64
  ],
  "races": 3,
  "sc": [
   0.77,
   2,
   10
  ],
  "track_length": 4868.2,
  "vsc": [
   0.85,
   1,
   15
  ]
 },
 "French Grand Prix": {
  "gain": [
   1.18,
   1,
   8
  ],
  "pit_loss": [
   31.11,
   1,
   9
  ],
  "races": 1,
  "sc": [
   0.94,
   1,
   16
  ],
  "track_length": 5750.4
 },
 "Hungarian Grand Prix": {
  "gain": [
   3.43,
   4,
   132
  ],
  "pit_loss": [
   23.33,
   4,
   145
  ],
  "races": 4,
  "track_length": 4336.1,
  "vsc": [
   0.72,
   1,
   2
  ]
 },
 "Italian Grand Prix": {
  "gain": [
   2.29,
   4,
   89
  ],
  "pit_loss": [
   26.28,
   4,
   92
  ],
  "races": 4,
  "sc": [
   0.86,
   1,
   8
  ],
  "track_length": 5743.2,
  "vsc": [
   0.84,
   1,
   1
  ]
 },
 "Japanese Grand Prix": {
  "gain": [
   3.51,
   4,
   86
  ],
  "pit_loss": [
   24.81,
   5,
   166
  ],
  "races": 5,
  "sc": [
   0.71,
   3,
   21
  ],
  "track_length": 5770.2,
  "vsc": [
   0.86,
   1,
   2
  ]
 },
 "Las Vegas Grand Prix": {
  "gain": [
   2.7,
   2,
   55
  ],
  "pit_loss": [
   21.83,
   3,
   75
  ],
  "races": 3,
  "sc": [
   0.82,
   1,
   12
  ],
  "track_length": 6137.9,
  "vsc": [
   0.74,
   2,
   6
  ]
 },
 "Mexico City Grand Prix": {
  "gain": [
   3.43,
   4,
   87
  ],
  "pit_loss": [
   23.27,
   4,
   92
  ],
  "races": 4,
  "sc": [
   0.05,
   1,
   16
  ],
  "track_length": 4234.9
 },
 "Miami Grand Prix": {
  "gain": [
   2.23,
   5,
   72
  ],
  "pit_loss": [
   21.39,
   5,
   81
  ],
  "races": 5,
  "sc": [
   0.83,
   3,
   19
  ],
  "track_length": 5335.2,
  "vsc": [
   0.85,
   3,
   13
  ]
 },
 "Monaco Grand Prix": {
  "gain": [
   3.59,
   5,
   63
  ],
  "pit_loss": [
   22.17,
   5,
   167
  ],
  "races": 5,
  "sc": [
   0.35,
   3,
   53
  ],
  "track_length": 3278.9,
  "vsc": [
   0.79,
   1,
   4
  ]
 },
 "Qatar Grand Prix": {
  "gain": [
   2.03,
   3,
   77
  ],
  "pit_loss": [
   27.85,
   3,
   81
  ],
  "races": 3,
  "sc": [
   0.86,
   3,
   50
  ],
  "track_length": 5374.6
 },
 "Saudi Arabian Grand Prix": {
  "gain": [
   3.04,
   2,
   18
  ],
  "pit_loss": [
   21.26,
   4,
   42
  ],
  "races": 4,
  "sc": [
   0.91,
   4,
   38
  ],
  "track_length": 6095.7,
  "vsc": [
   0.86,
   1,
   1
  ]
 },
 "Singapore Grand Prix": {
  "gain": [
   3.92,
   2,
   45
  ],
  "pit_loss": [
   30.45,
   4,
   67
  ],
  "races": 4,
  "sc": [
   0.84,
   2,
   18
  ],
  "track_length": 4873.9,
  "vsc": [
   0.77,
   2,
   7
  ]
 },
 "Spanish Grand Prix": {
  "gain": [
   4.18,
   4,
   169
  ],
  "pit_loss": [
   23.44,
   4,
   178
  ],
  "races": 4,
  "sc": [
   0.78,
   1,
   14
  ],
  "track_length": 4623.6
 },
 "S\u00e3o Paulo Grand Prix": {
  "gain": [
   3.38,
   3,
   99
  ],
  "pit_loss": [
   22.67,
   4,
   146
  ],
  "races": 4,
  "sc": [
   0.7,
   3,
   5
  ],
  "track_length": 4237.0,
  "vsc": [
   0.69,
   3,
   14
  ]
 },
 "United States Grand Prix": {
  "gain": [
   3.15,
   4,
   100
  ],
  "pit_loss": [
   22.26,
   4,
   104
  ],
  "races": 4,
  "sc": [
   0.78,
   2,
   11
  ],
  "track_length": 5436.0,
  "vsc": [
   0.85,
   1,
   1
  ]
 }
}
