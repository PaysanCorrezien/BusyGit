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
    let
      # Define overlay that will add busygit to pkgs
      overlay = final: prev: {
        busygit = final.python3.pkgs.buildPythonApplication {
          pname = "busygit";
          version = "0.1";
          src = ./.;

          propagatedBuildInputs = with final.python3.pkgs; [
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

          meta = with final.lib; {
            description = "BusyGit - A Git utility tool for managing multiple repositories";
            homepage = "https://github.com/PaysanCorrezien/BusyGit";
            license = licenses.mit;
            mainProgram = "busygit";
            maintainers = with maintainers; [ ];
            platforms = platforms.all;
          };
        };
      };
    in
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [ overlay ];
        };
      in
      {
        packages.default = pkgs.busygit;

        # Expose the overlay
        overlays.default = overlay;

        # Development shell
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            python3
            python3Packages.pip
            python3Packages.virtualenv
          ];
        };
      }
    )
    // {
      # This makes the overlay available even on non-default systems
      overlays.default = overlay;
    };
}
