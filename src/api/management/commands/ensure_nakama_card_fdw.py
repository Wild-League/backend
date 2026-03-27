"""Expose Django ``card`` to Nakama's DB via postgres_fdw so Lua match code can ``SELECT`` stats."""

from __future__ import annotations

import os
from typing import Any

import psycopg2
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
	help = (
		'Creates postgres_fdw in the nakama database and imports public.card from the '
		'wildleague database. Run after migrations and seed_default_cards so match.lua can '
		'load card stats with nk.sql_query.'
	)

	def handle(self, *args: Any, **options: Any) -> None:
		host = os.environ.get('POSTGRES_HOST', 'localhost')
		port = os.environ.get('POSTGRES_PORT', '5432')
		user = os.environ.get('POSTGRES_USER', 'postgres')
		password = os.environ.get('POSTGRES_PASSWORD', '')
		wildleague_db = os.environ.get('POSTGRES_DB', 'wildleague')
		nakama_db = os.environ.get('NAKAMA_POSTGRES_DB', 'nakama')

		try:
			conn = psycopg2.connect(
				host=host,
				port=port,
				user=user,
				password=password,
				dbname=nakama_db,
			)
		except psycopg2.Error as e:
			raise CommandError(f'Could not connect to PostgreSQL database "{nakama_db}": {e}') from e

		conn.autocommit = True
		cur = conn.cursor()
		try:
			cur.execute('CREATE EXTENSION IF NOT EXISTS postgres_fdw;')
			cur.execute('DROP SERVER IF EXISTS wildleague_srv CASCADE;')
			cur.execute(
				"""
				CREATE SERVER wildleague_srv FOREIGN DATA WRAPPER postgres_fdw
				OPTIONS (host %s, dbname %s, port %s);
				""",
				(host, wildleague_db, port),
			)
			cur.execute(
				"""
				CREATE USER MAPPING FOR CURRENT_USER SERVER wildleague_srv
				OPTIONS (user %s, password %s);
				""",
				(user, password),
			)
			cur.execute('DROP FOREIGN TABLE IF EXISTS public.card CASCADE;')
			cur.execute(
				"""
				IMPORT FOREIGN SCHEMA public LIMIT TO (card)
				FROM SERVER wildleague_srv INTO public;
				"""
			)
		except psycopg2.Error as e:
			raise CommandError(
				f'FDW setup failed (ensure wildleague has migrated and public.card exists): {e}'
			) from e
		finally:
			cur.close()
			conn.close()

		self.stdout.write(self.style.SUCCESS(f'Foreign table public.card is available in "{nakama_db}".'))
