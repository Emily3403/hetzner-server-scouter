import asyncio

from hetzner_server_scouter.db.crud import download_server_list, update_server_list
from hetzner_server_scouter.db.db_conf import init_database, DatabaseSessionMaker
from hetzner_server_scouter.notifications.crud import read_notification_config, process_changes
from hetzner_server_scouter.settings import error_exit
from hetzner_server_scouter.utils import program_args, print_version


# TODO: Logs for what happened in the past
# TODO: Daily summary?
# TODO: Provide option to deploy systemd script

async def _main() -> None:
    init_database()

    if program_args.version:
        print_version()
        exit(0)

    with DatabaseSessionMaker() as db:
        config = read_notification_config(db)
        servers = await download_server_list()
        if servers is None:
            error_exit(1, "Failed to download the server list!")

        changes = update_server_list(db, servers)
        await process_changes(db, config, changes)

        # TODO: Move process changes into the main function

        _ = servers


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
