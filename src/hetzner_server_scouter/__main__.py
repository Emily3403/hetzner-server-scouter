import asyncio

from hetzner_server_scouter.db.crud import download_server_list, update_server_list
from hetzner_server_scouter.db.db_conf import init_database, DatabaseSessionMaker
from hetzner_server_scouter.notifications.crud import process_changes
from hetzner_server_scouter.notifications.notify_telegram import notify_exception_via_telegram
from hetzner_server_scouter.settings import error_exit
from hetzner_server_scouter.utils import program_args, print_version, print_exception


async def _main() -> None:
    init_database()

    if program_args.version:
        print_version()
        exit(0)

    with DatabaseSessionMaker() as db:
        servers = await download_server_list()
        if servers is None:
            error_exit(1, "Failed to download the server list!")

        changes = update_server_list(db, servers)
        await process_changes(db, changes)


def main() -> None:
    try:
        asyncio.run(_main())
    except Exception as ex:
        print_exception(ex)
        asyncio.run(notify_exception_via_telegram(ex))


if __name__ == "__main__":
    main()
