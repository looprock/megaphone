pkg_origin=looprock
pkg_name=megaphone
pkg_version=0.2.1
pkg_maintainer="Douglas Land <dsl@looprock.com>"
pkg_license=()
pkg_source=https://github.com/looprock/${pkg_name}/archive/${pkg_version}.tar.gz
pkg_shasum=c967a4bec7d70359ebfc325078097635945bb5c7d8262614762562f0a2c9ac36
pkg_filename=${pkg_name}-${pkg_version}.tar.gz
pkg_deps=(core/glibc core/python2)
pkg_build_deps=()
pkg_bin_dirs=(bin)
pkg_include_dirs=(include)
pkg_lib_dirs=(lib)
pkg_expose=(18001)
pkg_svc_run="${pkg_prefix}/bin/megaphone.py"

do_prepare() {
  # The `/usr/bin/env` path is hardcoded in tests, so we'll add a symlink since fix_interpreter won't work.
  if [[ ! -r /usr/bin/env ]]; then
    ln -sv $(pkg_path_for coreutils)/bin/env /usr/bin/env
    _clean_env=true
  fi
}

do_build() {
    pip install --upgrade pip
    pip install virtualenv
    virtualenv ${pkg_prefix}
}

do_install() {
    source ${pkg_prefix}/bin/activate
    mkdir -p ${pkg_prefix}/bin
    cp -vr megaphone/megaphone.py ${pkg_prefix}/bin/
    cp -v requirements.txt ${pkg_prefix}/bin/
    pip install -r ${pkg_prefix}/bin/requirements.txt
}
