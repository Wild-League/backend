"""Upsert the built-in card catalog (matches sql/default_deck.sql card rows).

On a brand-new database (no rows in ``card``), downloads PNGs from
https://github.com/Wild-League/base-cards-assets and uploads them to SeaweedFS
(S3 API), then stores public object URLs on each Card. Self-hosters run this
once after migrations.

If the catalog already exists, the command exits unless ``--force`` is passed
(re-applies defaults using remote URLs only; no upload).
"""

from __future__ import annotations

import os
from datetime import date
from decimal import Decimal
from typing import Any, TypedDict

import boto3
import requests
from botocore import UNSIGNED
from botocore.config import Config
from botocore.exceptions import ClientError
from botocore.exceptions import EndpointConnectionError
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from src.api.models import Card

# Upstream layout: <UPSTREAM>/<slug>/<file>.png
UPSTREAM = 'https://raw.githubusercontent.com/Wild-League/base-cards-assets/main'

# Files to mirror per slug (must match Card.img_* usage in _default_cards).
MIRROR_FILES: list[tuple[str, str]] = [
	('caveman', 'card.png'),
	('caveman', 'attack.png'),
	('caveman', 'death.png'),
	('caveman', 'walk.png'),
	('dino', 'card.png'),
	('dino', 'attack.png'),
	('dino', 'death.png'),
	('dino', 'walk.png'),
	('thunder', 'card.png'),
	('thunder', 'attack.png')
]


class CardSeedFields(TypedDict):
	"""Field payload for Card (see src.api.models.Card); excludes id (set via lookup)."""

	name: str
	type: str
	life: int | None
	speed: Decimal | None
	attack_range: Decimal | None
	cooldown: Decimal | None
	damage: Decimal | None
	frame_width: int | None
	frame_height: int | None
	created_at: date
	updated_at: date | None
	img_card: str | None
	img_preview: str | None
	img_attack: str | None
	img_death: str | None
	img_walk: str | None


def _u(base_url: str, slug: str, filename: str) -> str:
	"""base_url = prefix ending before /<slug>/<file> (GitHub root or …/bucket)."""
	return f"{base_url.rstrip('/')}/{slug}/{filename}"


def _endpoint_url() -> str:
	ep = settings.SEAWEED['S3_ENDPOINT']
	if ep.startswith('http://') or ep.startswith('https://'):
		return ep
	return f'http://{ep}'


def _candidate_endpoints() -> list[str]:
	primary = _endpoint_url().rstrip('/')
	candidates = [primary]
	if primary in ('http://localhost:8333', 'http://127.0.0.1:8333'):
		candidates.append('http://seaweedfs-s3:8333')
	return candidates


def _public_base_url() -> str:
	custom = (settings.SEAWEED.get('PUBLIC_BASE_URL') or '').strip()
	if custom:
		return custom.rstrip('/')
	ep = settings.SEAWEED['S3_ENDPOINT']
	if ep.startswith('http://') or ep.startswith('https://'):
		return ep.rstrip('/')
	return f'http://{ep}'.rstrip('/')


def _s3_client(endpoint_url: str):
	access = (settings.SEAWEED.get('ACCESS_KEY') or '').strip()
	secret = (settings.SEAWEED.get('SECRET_KEY') or '').strip()
	if not access or not secret:
		# SeaweedFS default mode allows anonymous S3 operations.
		return boto3.client(
			's3',
			endpoint_url=endpoint_url,
			region_name='us-east-1',
			config=Config(signature_version=UNSIGNED, s3={'addressing_style': 'path'}),
		)
	return boto3.client(
		's3',
		endpoint_url=endpoint_url,
		aws_access_key_id=access,
		aws_secret_access_key=secret,
		region_name='us-east-1',
		config=Config(signature_version='s3v4', s3={'addressing_style': 'path'}),
	)


def _ensure_bucket(client: Any, bucket: str) -> None:
	try:
		client.head_bucket(Bucket=bucket)
	except ClientError as e:
		code = (e.response.get('Error', {}).get('Code') or '').strip()
		# Some S3-compatible servers return AccessDenied for head_bucket even when
		# a bucket exists and object writes are still permitted for the caller.
		if code == 'AccessDenied':
			return
		try:
			client.create_bucket(Bucket=bucket)
		except ClientError as create_err:
			create_code = (create_err.response.get('Error', {}).get('Code') or '').strip()
			if create_code == 'AccessDenied':
				if code in ('404', 'NoSuchBucket', 'NotFound'):
					raise CommandError(
						f'Bucket "{bucket}" does not exist and current credentials are bucket-scoped. '
						'Grant temporary global Admin to bootstrap, run seed once, then scope down. '
						'Example: s3.configure -user=<user> -access_key=<key> -secret_key=<secret> '
						'-actions=Read,Write,List,Tagging,Admin -apply'
					) from create_err
				raise CommandError(
					f'Access denied creating bucket "{bucket}". '
					'Use credentials with Admin permission, or pre-create the bucket '
					'and grant Write permission to the configured key.'
				) from create_err
			if create_code in ('BucketAlreadyExists', 'BucketAlreadyOwnedByYou'):
				# Another identity may own it, or this identity already created it.
				return
			raise


def _mirror_to_seaweed(stdout: Any, style: Any) -> str:
	"""Download from UPSTREAM and upload to S3. Returns db base URL for _default_cards."""
	bucket = settings.SEAWEED['CARD_BUCKET']
	client = None
	last_err: Exception | None = None
	for endpoint in _candidate_endpoints():
		try:
			candidate = _s3_client(endpoint)
			_ensure_bucket(candidate, bucket)
			client = candidate
			if endpoint != _endpoint_url().rstrip('/'):
				stdout.write(style.WARNING(f'SeaweedFS fallback endpoint in use: {endpoint}'))
			break
		except EndpointConnectionError as e:
			last_err = e
			continue
		except ClientError as e:
			err_code = (e.response.get('Error', {}).get('Code') or '').strip()
			if err_code in ('BucketAlreadyExists', 'BucketAlreadyOwnedByYou'):
				client = candidate
				break
			last_err = e
			break
	if client is None:
		raise CommandError(
			'Could not connect to SeaweedFS S3 endpoint. '
			f"Configured SEAWEED_S3_ENDPOINT={settings.SEAWEED['S3_ENDPOINT']!r}. "
			'When running inside docker-compose, set SEAWEED_S3_ENDPOINT=seaweedfs-s3:8333. '
			f'Last error: {last_err}'
		)

	for slug, filename in MIRROR_FILES:
		src = f"{UPSTREAM.rstrip('/')}/{slug}/{filename}"
		key = f'{slug}/{filename}'
		stdout.write(f'Downloading {src} …')
		try:
			r = requests.get(src, timeout=120)
			r.raise_for_status()
		except requests.RequestException as e:
			raise CommandError(f'Failed to download {src}: {e}') from e
		try:
			client.put_object(
				Bucket=bucket,
				Key=key,
				Body=r.content,
				ContentType='image/png',
			)
		except ClientError as e:
			raise CommandError(f'Failed to upload s3://{bucket}/{key}: {e}') from e
		stdout.write(style.SUCCESS(f' OK → s3://{bucket}/{key}'))

	db_base = f'{_public_base_url()}/{bucket}'
	return db_base


def _default_cards(base_url: str) -> list[tuple[int, CardSeedFields]]:
	"""Legacy ids 1-3 for stable references; mirrors sql/default_deck.sql."""
	b = base_url
	created = date.fromisoformat('2024-03-02')
	return [
		(
			1,
			{
				'name': 'Caveman',
				'type': 'char',
				'life': 100,
				'speed': Decimal('1.00'),
				'attack_range': Decimal('40.00'),
				'cooldown': Decimal('6.00'),
				'damage': Decimal('100.00'),
				'frame_width': 60,
				'frame_height': 60,
				'created_at': created,
				'updated_at': None,
				'img_card': _u(b, 'caveman', 'card.png'),
				'img_preview': None,
				'img_attack': _u(b, 'caveman', 'attack.png'),
				'img_death': _u(b, 'caveman', 'death.png'),
				'img_walk': _u(b, 'caveman', 'walk.png'),
			},
		),
		(
			2,
			{
				'name': 'Dino',
				'type': 'char',
				'life': 300,
				'speed': Decimal('0.80'),
				'attack_range': Decimal('60.00'),
				'cooldown': Decimal('10.00'),
				'damage': Decimal('200.00'),
				'frame_width': 90,
				'frame_height': 90,
				'created_at': created,
				'updated_at': None,
				'img_card': _u(b, 'dino', 'card.png'),
				'img_preview': None,
				'img_attack': _u(b, 'dino', 'attack.png'),
				'img_death': _u(b, 'dino', 'death.png'),
				'img_walk': _u(b, 'dino', 'walk.png'),
			},
		),
		(
			3,
			{
				'name': 'Thunder',
				'type': 'spell',
				'life': None,
				'speed': Decimal('1.20'),
				'attack_range': Decimal('50.00'),
				'cooldown': Decimal('5.00'),
				'damage': Decimal('70.00'),
				'frame_width': 64,
				'frame_height': 64,
				'created_at': created,
				'updated_at': None,
				'img_card': _u(b, 'thunder', 'card.png'),
				'img_preview': None,
				'img_attack': _u(b, 'thunder', 'attack.png'),
				'img_death': None,
				'img_walk': None,
			},
		),
	]


class Command(BaseCommand):
	help = (
		'Create or update the default Card rows (ids 1-3). '
		'On an empty card table, mirrors assets from GitHub into SeaweedFS unless --skip-mirror.'
	)

	def add_arguments(self, parser) -> None:
		parser.add_argument(
			'--force',
			action='store_true',
			help=(
				'Re-apply defaults even if cards already exist. '
				'Uses remote URLs only (no mirror).'
			),
		)
		parser.add_argument(
			'--base-url',
			default=None,
			help=(
				'URL prefix for PNGs when not mirroring: <base>/<slug>/<file>. '
				'Default: CARD_ASSET_BASE_URL env or GitHub raw main.'
			),
		)

	def handle(self, *args: Any, **options: Any) -> None:
		force: bool = options['force']
		base_url_opt: str | None = options['base_url']

		if Card.objects.exists() and not force:
			self.stdout.write(
				self.style.WARNING(
					'Card catalog already exists; skipped (brand-new seed only). '
					'Use --force to re-apply defaults from remote URLs (no upload).'
				)
			)
			return

		is_empty = not Card.objects.exists()
		if is_empty:
			db_base = _mirror_to_seaweed(self.stdout, self.style)
			self.stdout.write(self.style.NOTICE(f'Storing card URLs under: {db_base}/'))
		else:
			db_base = base_url_opt or os.environ.get(
				'CARD_ASSET_BASE_URL',
				UPSTREAM,
			)

		rows = _default_cards(db_base)
		with transaction.atomic():
			for card_id, defaults in rows:
				_, created = Card.objects.update_or_create(
					id=card_id,
					defaults=defaults,
				)
				action = 'Created' if created else 'Updated'
				self.stdout.write(f"{action} card {card_id} ({defaults['name']})")
		self.stdout.write(self.style.SUCCESS(f'Done. Image URL prefix: {db_base}'))
