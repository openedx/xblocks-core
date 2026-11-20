(function(requirejs, require, define) {
    /*
    Use the Problem block's translation catalog (window.XBlockProblemI18N, loaded by the
    block's view) and fall back to the platform's global catalog.
    */
    function gettext(msgid) {
        var catalog = window.XBlockProblemI18N || window;
        return catalog.gettext ? catalog.gettext(msgid) : msgid;
    }

    define(['edx-ui-toolkit/js/utils/html-utils'], function(HtmlUtils) {
        return BaseImage;

        function BaseImage(state) {
            var $baseImageElContainer;

            $baseImageElContainer = $(HtmlUtils.joinHtml(
                HtmlUtils.HTML('<div class="base_image_container" style=" position: relative; margin-bottom: 25px; '),
                HtmlUtils.HTML('margin-left: auto; margin-right: auto; " ></div>')
            ).toString());

            state.baseImageEl = $('<img />', {
                alt: gettext('Drop target image')
            });

            state.baseImageEl.attr('src', state.config.baseImage);
            state.baseImageEl.load(function() {
                $baseImageElContainer.css({
                    width: this.width,
                    height: this.height
                });

                state.baseImageEl.appendTo($baseImageElContainer);
                $baseImageElContainer.appendTo(state.containerEl);

                state.baseImageEl.mousedown(function(event) {
                    event.preventDefault();
                });

                state.baseImageLoaded = true;
            });
            state.baseImageEl.error(function() {
                var errorMsg = HtmlUtils.joinHtml(
                    HtmlUtils.HTML('<span style="color: red;">'),
                    HtmlUtils.HTML('ERROR: Image "'), state.config.baseImage, HtmlUtils.HTML('" was not found!'),
                    HtmlUtils.HTML('</span>')
                );
                console.log('ERROR: Image "' + state.config.baseImage + '" was not found!');
                HtmlUtils.setHtml($baseImageElContainer, errorMsg);
                $baseImageElContainer.appendTo(state.containerEl);
            });
        }
    }); // End-of: define([], function () {
}(RequireJS.requirejs, RequireJS.require, RequireJS.define)); // End-of: (function (requirejs, require, define) {
