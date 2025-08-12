# AI Models

Lexiflux use AI models to create `AI Insights` in `Sidebar`
(you open it with blue binocular icon).

Also you can use AI for inline text translation. By default
it uses Google Translate.

To configure Sidebar and inline translation see [Dictionary & AI Insights Settings](http://localhost:6100/language-preferences/).
There are separate settings for each language, so you can configure
different settings for different languages.

## AI Insights Types

### AI Powered (Translate, Lexical, Origin, Explain, Sentence)
They use predefined prompts to generate insights.
You can select AI model (ChatGPT, Claude etc) to run them.

#### Custom AI
With type "AI" you can define your own prompt for AI model.

### Dictionary
There are a number of dictionaries embedded like Google Translate, Linguee Translator, MyMemory Translator, PONS Translator.

### Site
You define what a URL to open and with which parameters.
This is usefull for good translator that does not have API. Like glosbe.com.

Most of them should be open in external window, but some of them even could be open inside the Sidebar.

This is controlled by `open in new window` parameter.

## AI models: OpenAI (ChatGPT), Anthropic (Claude) and others

To use commercial AI providers you need `API KEY`.

See [AI Connections](http://localhost:6100/ai-settings/) section how to get one for different AI providers.

## Ollama
You can [install](docker.md#local-ollama-ai) in the docker local AI [Ollama](https://github.com/jmorganca/ollama) model.

It is free, but requires about 4G RAM to run. Remember this is RAM for the Docker container, not for the host machine.

And it is not so smart as commercial models from OpenAI and Anthropic.
