{
  description = "Python and Frontend development environment";
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };
  outputs = {nixpkgs, ...}: let
    system = "x86_64-linux";
    pkgs = import nixpkgs {
      inherit system;
      config.permittedInsecurePackages = ["pnpm-12.11.2"];
    };
  in {
    devShells.${system}.default = pkgs.mkShell {
      packages = with pkgs; [
        biome
        firefox
        geckodriver
        git
        just
        nodejs
        prek
        uv
        vtsls
        vue-language-server
        python314
      ];
    };
  };
}
