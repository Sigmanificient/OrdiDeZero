{
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = {
    self,
    nixpkgs,
  }: let
    applySystems = nixpkgs.lib.genAttrs ["x86_64-linux"];
    eachSystem = f: applySystems (system: f nixpkgs.legacyPackages.${system});
  in {
    formatter = eachSystem (pkgs: pkgs.alejandra);
    devShells = eachSystem (pkgs: {
      default = pkgs.mkShell {
        packages = with pkgs; [
          gcc
          SDL2
        ];
      };
    });
  };
}
