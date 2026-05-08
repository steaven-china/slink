# Maintainer: Steaven Jiang
pkgname=slink
pkgver=0.1.0
pkgrel=1
pkgdesc="Secure SSH Connection Manager with encrypted storage"
arch=('x86_64')
url=""
license=('MIT')
depends=()
makedepends=('python' 'python-click' 'python-cryptography' 'nuitka' 'patchelf' 'gcc')
source=()
sha256sums=()

build() {
    cd "$startdir"
    python -m nuitka \
        --onefile \
        --standalone \
        --remove-output \
        --disable-plugin=pkg-resources \
        --include-package=click \
        --include-package=cryptography \
        --output-filename=sli \
        slink.py
}

package() {
    cd "$startdir"
    install -Dm755 sli "$pkgdir/usr/bin/sli"
    install -Dm644 README.md "$pkgdir/usr/share/doc/$pkgname/README.md"
}
