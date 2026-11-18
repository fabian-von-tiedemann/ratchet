gh api graphql -f query='mutation { updateRepository(input: {repositoryId: "x", hasWikiEnabled: false}) { clientMutationId } }'
