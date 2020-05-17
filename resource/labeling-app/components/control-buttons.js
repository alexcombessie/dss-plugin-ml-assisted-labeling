import {DKUApi} from "../dku-api.js";

export let ControlButtons = {
    props: ['isFirst', 'canSkip', 'isLabeled'],
    data: () => {
        return {isLast: true}
    },
    methods: {
        back: function () {
            if (!this.$root.canLabel || this.isFirst) {
                return;
            }
            DKUApi.back(this.$root.item.labelId).then(this.processAnnotationResponce);
        },
        next: function () {
            if (!this.$root.canLabel || !this.isLabeled) {
                return;
            }
            if (this.isLast) {
                this.unlabeled();
            } else {
                DKUApi.next(this.$root.item.labelId).then(this.processAnnotationResponce);
            }
        },
        processAnnotationResponce: function (data) {
            this.$root.item = data.item;
            this.$root.annotation = data.annotation;
            this.$root.savedAnnotation = _.cloneDeep(data.annotation);
            this.$root.isFirst = data.isFirst;
            this.isLast = data.isLast;
        },
        first: function () {
            DKUApi.first().then(this.processAnnotationResponce);
        },
        unlabeled: function () {
            if (!this.isLabeled) {
                return
            }
            this.$root.assignNextItem();
        },
        skip: function () {
            if (!this.$root.canLabel) {
                return;
            }
            const skipLabel = {
                "dataId": this.$root.item.id,
                "labelId": this.$root.item.labelId,
                "comment": this.$root.annotation.comment
            };

            DKUApi.skip(skipLabel).then((response) => {
                this.$root.updateStatsAndProceedToNextItem(response);
            });
        }
    },
    mounted: function () {
        window.addEventListener("keyup", (event) => {
            if (event.code === 'Enter') {
                this.skip();
            }
            if (event.code === 'ArrowLeft') {
                this.back();
            }
            if (event.code === 'ArrowRight' || event.code === 'Space') {
                this.next();
            }
        }, false);
    },
    template: `<div class="control-buttons">
    <button class="right-panel-button" :disabled="isFirst" @click="first()"><i class="fas fa-step-backward"></i></button>
    <button class="right-panel-button" :disabled="isFirst" @click="back()"><i class="fas fa-chevron-left"></i><span>back</span><code class="keybind"><i class="fas fa-arrow-left"></i></code></button>
    <button class="right-panel-button" @click="skip()"><span>skip</span><code class="keybind">Enter</code></button>
    <v-popover :trigger="'hover'" :placement="'bottom'">
        <button class="right-panel-button" @click="next()" :disabled="!isLabeled"><span>next</span><code class="keybind"><i class="fas fa-arrow-right"></i></code></button>
        <div slot="popover">
            Alternative hotkey: <code class="keybind" style="vertical-align: baseline">Space</code>
        </div>
    </v-popover>
<!--    <button class="right-panel-button" @click="next()" ><span>next</span><i class="fas fa-chevron-right"></i><code class="keybind"><i class="fas fa-arrow-right"></i></code></button>-->
    <button class="right-panel-button" :disabled="!isLabeled" @click="unlabeled()"><i class="fas fa-step-forward"></i></button></div>
`
};
