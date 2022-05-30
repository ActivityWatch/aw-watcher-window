from aw_watcher_window import main

# without this guard, running __main__.py directly will result in a multiprocess
# related error on macos. This makes it challenging to debug the window watcher on macos
if __name__ == "__main__":
  main()
