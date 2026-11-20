describe('XBlockProblemI18nUtils', function() {
    'use strict';

    var i18n = window.XBlockProblemI18nUtils;

    afterEach(function() {
        delete window.XBlockProblemI18N;
    });

    describe('with the block catalog loaded', function() {
        beforeEach(function() {
            window.XBlockProblemI18N = {
                gettext: function(msgid) { return 'block:' + msgid; },
                ngettext: function(singular, plural, count) { return 'block:' + (count === 1 ? singular : plural); }
            };
        });

        it('uses the block catalog for gettext', function() {
            expect(i18n.gettext('unsubmitted')).toEqual('block:unsubmitted');
        });

        it('uses the block catalog for ngettext', function() {
            expect(i18n.ngettext('point', 'points', 2)).toEqual('block:points');
        });
    });

    describe('without the block catalog', function() {
        it('falls back to the global gettext', function() {
            spyOn(window, 'gettext').and.returnValue('global:unsubmitted');
            expect(i18n.gettext('unsubmitted')).toEqual('global:unsubmitted');
            expect(window.gettext).toHaveBeenCalledWith('unsubmitted');
        });

        it('falls back to the global ngettext', function() {
            spyOn(window, 'ngettext').and.returnValue('global:points');
            expect(i18n.ngettext('point', 'points', 2)).toEqual('global:points');
            expect(window.ngettext).toHaveBeenCalledWith('point', 'points', 2);
        });
    });
});
