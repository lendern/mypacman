| version | id | description |
|---------|----|-------------|
| 1 | 1-1 | le jeu est jouable dans un terminal shell de taille 128x96 |
| 1 | 1-2 | au démarrage, l'air de jeu apparait dans la fenetre et est délimitée par des caractères "double-bar" |
| 1 | 1-3 | au démarrage, le PP apparait au centre de l'aire de jeu |
| 1.1 | 1-4 | le PP se déplace avec les 4 flèches directionnelles (← ↑ → ↓) |
| 1.1 | 1-5 | le PP est rendu comme une seule cellule graphique: une boule (Unicode) colorisée (ANSI) |
| 1.1 | 1-6 | rendu optimisé: draw complet au démarrage + mises à jour incrémentales (minimiser scintillement) |
| 1.1 | 1-7 | gestion d'entrée non bloquante: vidage du buffer OS pour éviter les mouvements résiduels après relâche |
| 1.1 | 1-8 | comportement de maintien de touche affiné: « gap-fill » pour éviter un micro-arrêt lors d'un maintien continu |
| 1.1 | 1-9 | CLI disponible à la racine (`mypacman-cli`) lançant `src.mypacman.main` |
| 1.1 | 1-10 | suite de tests minimale fournie (`tests/test_game.py`) couvrant comportements critiques |

```

## Objectif

Décrire l'état actuel du jeu terminal "mypacman" et les choix d'architecture retenus pour la version implémentée.

## Contraintes
- Terminal ciblé: Unix-like (ex. Ubuntu). Utilisation d'échappements ANSI et d'Unicode (●). 
- Taille minimale d'écran: 80 colonnes x 24 lignes (le jeu vérifie la taille au démarrage).
- Interaction: clavier (flèches), touche `q` pour quitter.
- Dépendances: aucune dépendance runtime externe (rendu/entrées en standard lib). Les tests utilisent `pytest` uniquement.

## Architecture (résumé)
- Board: modèle pur de l'aire de jeu, génération de la matrice avec bordures en double-bar.
- Renderer: responsable de l'I/O terminal — effectue un draw complet au démarrage puis des mises à jour incrémentales (position du joueur) pour réduire le scintillement. Masque/affiche le curseur et applique des couleurs ANSI.
- InputHandler: lecture non bloquante en mode raw. Lit et vide le buffer OS chaque tick, interprète les séquences d'échappement des flèches, renvoie la dernière direction valide et gère `q`.
- Game: orchestrateur — boucle principale, application des mouvements, clamp des positions, appel au renderer.
- Player: petite abstraction de position (x,y) et opérations de déplacement.

## Interfaces essentielles
- Entrées: séquences clavier (flèches, q). get_direction(timeout) retourne un vecteur directionnel (dx,dy) ou None.
- Sorties: écriture sur stdout via séquences ANSI (curseur, couleurs). Renderer expose `draw_full(board, player)` et `update_player(prev, new)`.

## Comportement d'entrée et robustesse
- Non-bloquant: `InputHandler` utilise `select`/`os.read` et n'appelle `fileno()` qu'à l'initialisation pour rester testable.
- Drain buffer: chaque tick, on lit un grand bloc disponible et on en extrait la dernière séquence flèche pertinente, évitant ainsi que des répétitions OS post-relâche continuent d'être appliquées.
- Gap-fill: pour atténuer le délai de répétition matériel qui provoque un court arrêt lors d'un maintien, le code peut émettre un mouvement supplémentaire contrôlé au début du maintien. Ce comportement est documenté et ajustable.

## Rendu et performance
- Rendu initial: draw complet du plateau et du joueur.
- Mises à jour: quand le joueur bouge, `update_player(prev, new)` n'efface que les cellules nécessaires (ancienne et nouvelle position) — réduction mesurable du scintillement.
- Couleurs: utilisation d'ANSI SGR pour coloriser le PP (ex. blanc/brillant) et la bordure.

## CLI et exécution
- Entrée utilisateur: lancer le binaire script `mypacman-cli` depuis la racine du dépôt, qui exécute `python -m src.mypacman.main` en ajoutant `src` au PYTHONPATH.
- Tests: lancer `pytest` depuis la racine pour exécuter la suite minimale.

## Tests et validation
- Fichiers: `tests/test_game.py` (spawn au centre, quitter sur `q`).
- Mouvement/clamp: `tests/test_movement.py` vérifie un pas à droite et le bridage à la bordure droite.
- Contraintes de test: `InputHandler` évite d'interroger `fileno()` à la construction pour rester compatible avec l'environnement pytest.

## Limitations et prochaines améliorations
- IA, ennemis, points, collisions et logique de score ne sont pas encore implémentés (scope actuel: PP mobile et rendu/IO fiables).
- Amélioration possible: paramétrer le délai et le taux de répétition logiciel pour reproduire/tuner le comportement des OS differents.
- Ajout d'une petite doc utilisateur (README run/play) et d'un script d'installation optionnel sont recommandés.

## Historique des versions
- 1.0: spécifications initiales (128x96).
- 1.1: ajustements appliqués — passage à 80x24, architecture Board/Renderer/InputHandler/Game, rendu incrémental, robustesse d'entrée et CLI/tests ajoutés.
- 1.1.1: nettoyage (suppression des constantes obsolètes, aucune dépendance `curses`) et ajout de tests mouvement+clamp.
