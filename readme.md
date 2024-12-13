# Git Tracker TUI

Git Tracker TUI is a terminal user interface (TUI) application built with Python and the Textual library. It allows users to monitor multiple Git repositories, either by specifying individual repositories or by watching directories containing multiple repositories. The application uses a configuration file to store the list of directories and repositories to monitor.

## Features

- **Directory Monitoring**: Watch specified directories for Git repositories.
- **Individual Repository Monitoring**: Monitor specific Git repositories.
- **Configuration File**: Use a TOML or YAML file to store the list of directories and repositories to monitor.
- **XDG Path Support**: Store configuration files in XDG-compliant directories.
- **User Interface**: Provide a TUI for easy interaction and monitoring.

## Development Tasks

3. **Directory and Repository Monitoring**: Implement logic to identify and monitor Git repositories in specified directories.
4. **Build TUI whith Textual**: Design and implement the TUI using the Textual library.
5. **XDG Path Integration**: Ensure configuration files are stored and accessed using XDG-compliant paths.
6. **Testing**: Write tests to ensure all functionalities work as expected.
7. **Documentation**: Document the code and provide user guides.

## TODO

### Priority

- [ ] Add searchable repository list for quick focus
- [ ] Add `open` command to launch $EDITOR in repository
- [ ] Add `git` command to launch lazygit (configurable) in repository
- [ ] make these command configurable via setttings
- [x] create enum for remote_status and refactor for it
- [x] create enum for local status and refactor for it
- [ ] use these as reference for styling the datatable
- [ ] Improve repository list visualization with color codes and icons
- [ ] make the first load not show error but keep empty with a loading animation under infos are ready

### Backlog

- [ ] Make settings view fully configurable
- [ ] Handle HTTPS repositories and SSH-less configurations ( bypass git.config ?)
- [ ] Refactor codebase
- [ ] Use JSONC for config to support in-file documentation
- [ ] Fix command palette color updates in settings file
- [ ] Add configurable key bindings with Vim-style navigation
  - Support k/j, Ctrl-n/Ctrl-p, Ctrl-d/Ctrl-u for logs
- [ ] Add loading animation during refresh operations
- [ ] Enhance UI/UX
- [ ] Add confiurable log level ( and only logs depending on this level)
- [ ] Add support for logpath settings ( and store default not on `~/.config`

### Nice to have

- [ ] Display total number of managed repositories in main UI
- [ ] Improve configuration
- [ ] Optimize refresh triggers (avoid full refresh when possible) -> fix the settings triggering full refresh
- [ ] Implement dashboard view

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## License

This project is licensed under the MIT License.
