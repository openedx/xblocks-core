/**
 * Translation functions for this block's JS.
 *
 * Uses the block's own catalog (`window.XBlockVideoI18N`, set by `i18n_js_namespace` and loaded
 * by the block's view before this bundle). Falls back to the platform's global catalog, and
 * then to the untranslated string.
 *
 * Webpack's ProvidePlugin injects these wherever the bundle uses `gettext`, `ngettext` or
 * `interpolate`, so call sites stay unchanged.
 */

function catalog() {
    return window.XBlockVideoI18N || window;
}

export function gettext(msgid) {
    const ns = catalog();
    return ns.gettext ? ns.gettext(msgid) : msgid;
}

export function ngettext(singular, plural, count) {
    const ns = catalog();
    if (ns.ngettext) {
        return ns.ngettext(singular, plural, count);
    }
    return count === 1 ? singular : plural;
}

export function interpolate(fmt, obj, named) {
    const ns = catalog();
    return (ns.interpolate || window.interpolate)(fmt, obj, named);
}
