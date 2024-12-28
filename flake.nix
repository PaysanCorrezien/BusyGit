{
  description = "BusyGit - A Git utility tool for managing multiple repositories";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python3;
      in
      {
        packages.default = python.pkgs.buildPythonApplication {
          pname = "busygit";
          version = "0.1";
          src = ./.;

          propagatedBuildInputs = with python.pkgs; [
            gitdb
            gitpython
            linkify-it-py
            markdown-it-py
            mdit-py-plugins
            mdurl
            platformdirs
            pygments
            rich
            smmap
            textual
            typing-extensions
            uc-micro-py
          ];

          doCheck = false;

          meta = with pkgs.lib; {
            description = "BusyGit - A Git utility tool for managing multiple repositories";
            homepage = "https://github.com/PaysanCorrezien/BusyGit";
            license = licenses.mit; # Update this if you're using a different license
            maintainers = with maintainers; [ ];
          };
        };

        defaultPackage = self.packages.${system}.default;

        # Add a devShell for development
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            python3
            python3Packages.pip
            python3Packages.virtualenv
          ];
        };
      }
    );
}
