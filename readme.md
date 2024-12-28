# Git Tracker TUI

Git Tracker TUI is a terminal user interface (TUI) application built with Python and the Textual library. It allows users to monitor multiple Git repositories, either by specifying individual repositories or by watching directories containing multiple repositories. The application uses a configuration file to store the list of directories and repositories to monitor.

## Installation

You can install BusyGit using one of these methods:

### Using Pip

Install directly from GitHub:

```bash
pip install git+https://github.com/PaysanCorrezien/BusyGit.git
```

Then run with:

```bash
busygit
```

### Using Nix

#### Nix run

```bash
nix run github:PaysanCorrezien/BusyGit
```

#### Flakes

```nix
{
  inputs.busygit.url = "github:PaysanCorrezien/BusyGit";

  outputs = { self, nixpkgs, busygit }: {
    nixosConfigurations.mysystem = nixpkgs.lib.nixosSystem {
      modules = [
        {
          nixpkgs.overlays = [ busygit.overlays.default ];
          environment.systemPackages = with pkgs; [
            busygit
          ];
        }
      ];
    };
  };
}
```

### Manual Installation

Clone and install from source:

```bash
git clone https://github.com/PaysanCorrezien/BusyGit.git
cd BusyGit
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
pip install -r requirements.txt
python -m busygit.main
```

## Features

```

Would you like me to add any additional details or modify any of the installation instructions?


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

- [x] Add searchable repository list for quick focus
- [x] Add `open` command to launch $EDITOR in repository
- [x] Add `git` command to launch lazygit (configurable) in repository
- [x] make these command configurable via setttings
- [x] create enum for remote_status and refactor for it
- [x] create enum for local status and refactor for it
- [x] use these as reference for styling the datatable
- [ ] Improve repository list visualization with color codes and icons
- [x] make the first load not show error but keep empty with a loading animation under infos are ready
- [x] Make sorting modes (configurable) to quickly find repo that need to be fixed

### Backlog

- [ ] Make settings view fully configurable
- [ ] Handle HTTPS repositories and SSH-less configurations ( bypass git.config ?)
- [ ] Refactor codebase
- [ ] Use JSONC for config to support in-file documentation
- [ ] FIX dump default to config file if not present to guide
- [ ] Fix command palette color updates in settings file
- [ ] Add $env variable support
- [ ] Add configurable key bindings with Vim-style navigation
  - Support k/j, Ctrl-n/Ctrl-p, Ctrl-d/Ctrl-u for logs
- [x] Add loading animation during refresh operations
- [ ] Enhance UI/UX
- [ ] Add confiurable log level ( and only logs depending on this level)
- [ ] Add support for logpath settings ( and store default not on `~/.config`

### Nice to have

- [ ] Display total number of managed repositories in main UI
- [ ] Improve configuration
- [ ] Optimize refresh triggers (avoid full refresh when possible) -> fix the settings triggering full refresh
- [ ] make the open repo in browser work in input ( ctrl u alreadu used)
- [ ] Implement dashboard view

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## License

This project is licensed under the MIT License.
```
