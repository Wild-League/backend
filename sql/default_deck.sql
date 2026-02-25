insert into "public"."card"
	(
		"attack_range",
		"cooldown",
		"created_at",
		"damage",
		"frame_height",
		"frame_width",
		"id",
		"img_attack",
		"img_card",
		"img_death",
		"img_preview",
		"img_walk",
		"life",
		"name",
		"speed",
		"type",
		"updated_at"
	)
values
	('40.00', '6.00', '2024-03-02', '100.00', 60, 60, 1, 'https://wild-minio.fly.dev/cards/caveman/attack.png', 'https://wild-minio.fly.dev/cards/caveman/card.png', 'https://wild-minio.fly.dev/cards/caveman/death.png', 'https://wild-minio.fly.dev/cards/caveman/preview.png', 'https://wild-minio.fly.dev/cards/caveman/walk.png', 100, 'Caveman', '1.00', 'char', NULL),
	('60.00', '10.00', '2024-03-02', '200.00', 90, 90, 2, 'https://wild-minio.fly.dev/cards/dino/attack.png', 'https://wild-minio.fly.dev/cards/dino/card.png', 'https://wild-minio.fly.dev/cards/dino/death.png', 'https://wild-minio.fly.dev/cards/dino/preview.png', 'https://wild-minio.fly.dev/cards/dino/walk.png', 300, 'Dino', '0.80', 'char', NULL),
	('50.00', '5.00', '2024-03-02', '70.00', 64, 64, 3, 'https://wild-minio.fly.dev/cards/thunder/attack.png', 'https://wild-minio.fly.dev/cards/thunder/card.png', NULL, NULL, NULL, NULL, 'Thunder', '1.20', 'spell', NULL)
;


INSERT INTO deck (name, is_selected, created_at, user_id) values ('default', TRUE, current_date, 26);
INSERT INTO deck (name, is_selected, created_at, user_id) values ('default', TRUE, current_date, 27);

INSERT INTO deck_card (card_id, deck_id) values (1, 2);
INSERT INTO deck_card (card_id, deck_id) values (2, 2);
INSERT INTO deck_card (card_id, deck_id) values (3, 2);


INSERT INTO deck_card (card_id, deck_id) values (1, 3);
INSERT INTO deck_card (card_id, deck_id) values (2, 3);
INSERT INTO deck_card (card_id, deck_id) values (3, 3);
