import os
from glob import glob
from os.path import join

from pythonforandroid.recipe import RustCompiledComponentsRecipe


class WreqRecipe(RustCompiledComponentsRecipe):
    version = "0.12.0"
    url = "https://files.pythonhosted.org/packages/source/w/wreq/wreq-{version}.tar.gz"
    site_packages_name = "wreq"

    def get_recipe_env(self, arch, **kwargs):
        env = super().get_recipe_env(arch, **kwargs)
        llvm = self.ctx.ndk.llvm_prebuilt_dir
        clang_include = glob(join(llvm, "lib", "clang", "*", "include"))[0]

        # maturin's isolated subprocess does not inherit the image ENV, so explicitly feed rustup and force the toolchain (works around "no default")
        env["RUSTUP_HOME"] = os.environ.get("RUSTUP_HOME", "/opt/rustup")
        env["RUSTUP_TOOLCHAIN"] = "stable"
        # the image's /opt/cargo is root read-only; the builder can't write downloaded crates there, so use the writable home cargo
        env["CARGO_HOME"] = join(os.path.expanduser("~"), ".cargo")
        # the android target can't pass auditwheel (non-manylinux), skip (same as upstream CI)
        env["MATURIN_PEP517_ARGS"] = "--skip-auditwheel"
        # btls-sys 0.5.6 builds BoringSSL via the NDK cmake toolchain and needs this pointer
        env["ANDROID_NDK_HOME"] = self.ctx.ndk_dir
        # the image's built-in cmake 3.25 fails FindThreads under the NDK toolchain, use an isolated cmake>=4
        env["CMAKE"] = "/opt/cmake4/bin/cmake"
        # bindgen generates bindings for BoringSSL; libclang lives under the NDK's musl/lib
        env["LIBCLANG_PATH"] = join(llvm, "musl", "lib")
        env["BINDGEN_EXTRA_CLANG_ARGS"] = (
            f"--target=aarch64-linux-android{self.ctx.ndk_api} "
            f"--sysroot={self.ctx.ndk.sysroot} -isystem {clang_include}"
        )
        env["PATH"] = join(llvm, "bin") + ":" + env["PATH"]
        return env


recipe = WreqRecipe()
