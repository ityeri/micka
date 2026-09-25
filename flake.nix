{
  description = "uv + pygame native (SDL2) build shell";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { nixpkgs, ... }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
      nativeDeps =
        pkgs:
        with pkgs;
        [
          SDL2
          SDL2_image
          SDL2_mixer
          SDL2_ttf
          portmidi
          libpng
          libjpeg_turbo
          freetype
          libx11
          fontconfig
        ];
    in
    {
      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShell {
          packages = with pkgs; [
            uv
            python314
            pkg-config
          ];

          buildInputs = nativeDeps pkgs;

          env = {
            UV_PYTHON = pkgs.lib.getExe pkgs.python314;
            PYGAME_EXTRA_BASE = pkgs.lib.concatStringsSep ":" (
              pkgs.lib.concatMap (d: [
                "${pkgs.lib.getDev d}"
                "${pkgs.lib.getLib d}"
              ]) (nativeDeps pkgs)
            );
          };
        };
      });
    };
}