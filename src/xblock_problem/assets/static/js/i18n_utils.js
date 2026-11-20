/**
 * Translation functions for this block's JS.
 *
 * Uses the block's own catalog (`window.XBlockProblemI18N`, set by `i18n_js_namespace` and loaded
 * by the block's view before this bundle). Falls back to the platform's global catalog, and
 * then to the untranslated string.
 *
 * Webpack's ProvidePlugin injects these wherever the bundle uses `gettext` or `ngettext`, so
 * call sites stay unchanged.
 *
 * Written as UMD so Karma, which loads the raw files rather than the bundle, can test it through
 * `window.XBlockProblemI18nUtils`.
 */
(function(root, factory) {
    'use strict';

    var api = factory(root);
    if (typeof module === 'object' && module.exports) {
        module.exports = api;
    } else {
        root.XBlockProblemI18nUtils = api;
    }
}(typeof window !== 'undefined' ? window : this, function(root) {
    'use strict';

    function catalog() {
        return root.XBlockProblemI18N || root;
    }

    function gettext(msgid) {
        var ns = catalog();
        return ns.gettext ? ns.gettext(msgid) : msgid;
    }

    function ngettext(singular, plural, count) {
        var ns = catalog();
        if (ns.ngettext) {
            return ns.ngettext(singular, plural, count);
        }
        return count === 1 ? singular : plural;
    }

    return {gettext: gettext, ngettext: ngettext};
}));
