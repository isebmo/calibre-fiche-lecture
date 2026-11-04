#!/bin/sh
# Construit le zip de l'extension et, avec --install, l'installe dans calibre.
#   ./build.sh --pot      met à jour translations/messages.pot et les .po (xgettext/msgmerge requis)
set -e
cd "$(dirname "$0")"
CAL=/Applications/calibre.app/Contents/MacOS

if [ "$1" = "--pot" ]; then
  (cd plugin && xgettext --from-code=UTF-8 -L Python --keyword=_ --keyword=ngettext:1,2 --no-wrap \
     --package-name="Fiche de lecture" -o translations/messages.pot $(ls *.py | grep -v cli.py) \
   && for po in translations/*.po; do msgmerge -q -U --backup=none --no-wrap "$po" translations/messages.pot; done)
  echo "Mis à jour : plugin/translations/messages.pot et *.po"
  exit 0
fi

BUILD=$(mktemp -d)
trap 'rm -rf "$BUILD"' EXIT
(cd plugin && tar cf - --exclude cli.py --exclude __pycache__ --exclude '*.pyc' --exclude '*.po' \
   --exclude '*.pot' .) | (cd "$BUILD" && tar xf -)
# Traductions de l'interface : .po -> .mo
for po in plugin/translations/*.po; do
  mo="$BUILD/translations/$(basename "${po%.po}").mo"
  if command -v msgfmt >/dev/null; then
    msgfmt -c -o "$mo" "$po"
  else
    "$CAL/calibre-debug" -c "from calibre.translations.msgfmt import make; make('$po', '$mo')"
  fi
done
rm -f fiche_lecture_gemini.zip
(cd "$BUILD" && zip -q -r - .) > fiche_lecture_gemini.zip
echo "Créé : fiche_lecture_gemini.zip"
unzip -l fiche_lecture_gemini.zip | tail -n +4 | awk '{print "  " $4}' | grep -v '^  $'
if [ "$1" = "--install" ]; then
  CC=calibre-customize; command -v $CC >/dev/null || CC=$CAL/calibre-customize
  $CC -a fiche_lecture_gemini.zip
fi
