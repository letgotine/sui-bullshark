import concurrent.futures
import random
import time

from loguru import logger
from pysui.sui.sui_config import SuiConfig

from config import total_max_8192_games_per_address, sleep_range_between_txs_in_sec, sleep_range_between_games_in_sec
from data import VERSION
from datatypes import Arrow
from utils import (add_logger,
                   read_mnemonics,
                   get_list_of_sui_configs,
                   execute_move_tx,
                   mint_game_tx,
                   short_address,
                   get_game_items_count,
                   get_active_game_ids,
                   get_sui_object_response, merge_sui_coins)


def main_play_game(sui_config: SuiConfig, game_id: str):
    game_over = False

    while not game_over:
        try:
            failed_arrow = True
            set_of_failed_arrows = set()

            while not game_over and failed_arrow:
                move = random.choice(list(set(Arrow) - set_of_failed_arrows))

                result = execute_move_tx(sui_config=sui_config, game_id=game_id, move=move)
                if result.reason:
                    logger.info(f'{short_address(result.address)} | {result.move.name:>6} | '
                                f'reason: direction is blocked.')

                    if get_sui_object_response(object_id=game_id).result.data.content.fields.game_over:
                        logger.warning(f'{short_address(result.address)} | game_id: {game_id} | reason: game is over.')
                        game_over = True
                    else:
                        set_of_failed_arrows.add(result.move)
                else:
                    failed_arrow = False
                    sleep = random.randint(sleep_range_between_txs_in_sec[0], sleep_range_between_txs_in_sec[1])
                    logger.info(f'{short_address(result.address)} | {result.move.name:>6} | '
                                f'digest: {result.digest} | sleep: {sleep}s.')
                    time.sleep(sleep)
        except:
            pass


def main_mint_game(sui_config: SuiConfig):
    result = mint_game_tx(sui_config=sui_config)
    if result.reason:
        logger.warning(f'{short_address(result.address)} | MINT | digest: {result.digest} | reason: {result.reason}.')
    else:
        logger.info(f'{short_address(result.address)} | MINT | digest: {result.digest}')


def single_executor(sui_config: SuiConfig):
    played_games = get_game_items_count(address=str(sui_config.active_address))

    while played_games < total_max_8192_games_per_address:
        active_game_8192_ids = get_active_game_ids(address=str(sui_config.active_address))

        if not active_game_8192_ids:
            merge_sui_coins(sui_config=sui_config)
            main_mint_game(sui_config=sui_config)
            time.sleep(random.randint(sleep_range_between_txs_in_sec[0], sleep_range_between_txs_in_sec[1]))
            active_game_8192_ids = get_active_game_ids(address=str(sui_config.active_address))

        random_game = random.choice(active_game_8192_ids)
        logger.info(f'{short_address(str(sui_config.active_address))} | current_game_id: {random_game}')
        main_play_game(sui_config=sui_config, game_id=random_game)

        sleep = random.randint(sleep_range_between_games_in_sec[0], sleep_range_between_games_in_sec[1])
        logger.info(f'{short_address(str(sui_config.active_address))} | sleep: {sleep}s.')
        time.sleep(sleep)

    logger.success(f'{short_address(str(sui_config.active_address))} | has played {played_games} games.')


def pool_executor(sui_configs: list[SuiConfig]):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(single_executor, sui_configs)


if __name__ == '__main__':
    add_logger(version=VERSION)
    try:
        mnemonics = read_mnemonics()
        sui_configs = get_list_of_sui_configs(mnemonics=mnemonics)

        logger.info('loaded addresses for 8192 game:')
        logger.info('-' * 66)

        for sui_config in sui_configs:
            logger.info(f'{sui_config.active_address}')

        logger.info('-' * 66)

        pool_executor(sui_configs=sui_configs)
    except Exception as e:
        logger.exception(e)
    except KeyboardInterrupt:
        exit()
