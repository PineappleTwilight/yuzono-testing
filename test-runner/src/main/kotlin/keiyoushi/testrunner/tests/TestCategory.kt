package keiyoushi.testrunner.tests

/**
 * Enum of all test categories.
 */
enum class TestCategory(val displayName: String) {
    STRUCTURAL("structural"),
    CONNECTIVITY("connectivity"),
    POPULAR("popular"),
    SEARCH("search"),
    LATEST("latest"),
    DETAILS("details"),
    EPISODES("episodes"),
    FILTERS("filters"),
    SERIES_DETAILS("series_details"),
    EPISODE_LIST("episode_list"),
    VIDEO_STREAMS("video_streams"),
    PAGINATION("pagination"),
    POST_SEARCH("post_search"),
    ;

    companion object {
        fun fromString(value: String): TestCategory? = entries.find { it.displayName == value.lowercase() }

        fun all(): Set<String> = entries.map { it.displayName }.toSet()
    }
}
