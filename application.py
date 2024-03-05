from app import application, config

if __name__ == '__main__':
    # parser = ArgumentParser()
    # help_str = "Whether to use the debug or production configuration (defaults to production)"
    # parser.add_argument('-d', '--debug', action='store_true', help=help_str)
    # args = parser.parse_args()
    if config.DEBUG:
        if config.DEV_SERVER_PROCESSES > 0:
            application.run(config.HOST, config.PORT, True,
                            processes=config.DEV_SERVER_PROCESSES, threaded=False)
        else:
            application.run(config.HOST, config.PORT, True)
    else:
        application.run(config.HOST, config.PORT, False)
