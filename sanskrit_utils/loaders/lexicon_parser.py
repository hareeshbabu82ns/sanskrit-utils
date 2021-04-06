from html.parser import HTMLParser
from indic_transliteration import sanscript
from indic_transliteration.sanscript import SchemeMap, SCHEMES, transliterate

# lexicon sample entry
# <H1><h><key1>AGrARa</key1><key2>AGrARa</key2></h><body><s>AGrARa tri0 A + GrA</s>—<s>kta . 1 gfhItaganDe puzpAdO nAsi-</s> <lb/><s>kayA yasya ganDajYAnaM jAtaM tasmin 2 tfpte ca BAve kta .</s> <lb/><s>3 ganGagrahaRe 4 tfptO ca na0 .</s></body><tail><L>6432</L><pc>0624,a</pc></tail></H1>


class LexiconHTMLParser(HTMLParser):
    tag_stack = []
    current_tag = ''
    mark_down = ''
    fromLang = sanscript.SLP1
    toLang = sanscript.DEVANAGARI
    key_fromLang = sanscript.SLP1
    key_toLang = sanscript.DEVANAGARI

    def init(self,
             key_fromLang=sanscript.SLP1,
             key_toLang=sanscript.DEVANAGARI,
             fromLang=sanscript.SLP1,
             toLang=sanscript.DEVANAGARI):
        self.fromLang = fromLang
        self.toLang = toLang
        self.key_fromLang = key_fromLang
        self.key_toLang = key_toLang

    def handle_starttag(self, tag, attrs):
        # print("Encountered a start tag:", tag)
        self.current_tag = tag
        self.tag_stack.append(tag)
        data = ''
        if tag == 'h':
            data = '**'
        elif tag.startswith('key'):
            data = ' _'
        elif tag in ['body', 'lb', 's']:
            data = '  \n'
        else:
            data = ''

        self.mark_down = self.mark_down + data

    def handle_endtag(self, tag):
        # print("Encountered an end tag :", tag)
        self.current_tag = self.tag_stack.pop()
        data = ''
        if tag == 'h':
            data = '**'
        elif tag.startswith('key'):
            data = '_ '
        else:
            data = ''
        self.mark_down = self.mark_down + data

    def handle_data(self, data):
        # print("Encountered some data  :", self.current_tag, ': ', data)
        final_data = data
        if self.current_tag in ['l', 'pc']:  # as of not not using this info
            return
        if self.current_tag in ['key1', 'key2'] and self.key_fromLang != self.key_toLang:
            final_data = transliterate(
                data, self.key_fromLang, self.key_toLang)
        if self.current_tag == 's' and self.fromLang != self.toLang:
            # sanskrit word
            final_data = transliterate(
                data, self.fromLang, self.toLang)

        self.mark_down = self.mark_down + final_data
