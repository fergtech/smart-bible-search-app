"""
Generate embeddings for all KJV verses and build FAISS index.
This script should be run once to create the semantic search cache.

Usage:
    python generate_embeddings.py [--force]
    
    --force: Regenerate embeddings even if cache exists
"""

import sys
sys.path.insert(0, 'backend')

import config  # type: ignore
import data_loader  # type: ignore
import search_semantic  # type: ignore


def main():
    """Generate embeddings and FAISS index."""
    # Check for force flag
    force = '--force' in sys.argv
    
    print("=" * 70)
    print("KJV Verse Embedding Generation")
    print("=" * 70)
    print(f"\nModel: {config.EMBEDDING_MODEL}")
    print(f"Output: {config.FAISS_INDEX_FILE}")
    print(f"Cache: {config.CACHE_DIR}\n")
    
    # Load verses
    print("Loading verses...")
    verses = data_loader.load_verses()
    
    stats = data_loader.get_verse_stats(verses)
    print(f"\n✓ Loaded {stats['total_verses']} verses from {stats['total_books']} books")
    
    if not stats['is_complete']:
        print(f"⚠ Warning: Expected {stats['canonical_verse_count']} verses")
        response = input("\nContinue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            return
    
    # Generate embeddings
    print("\n" + "=" * 70)
    print("Generating Embeddings")
    print("=" * 70)
    
    try:
        search_semantic.generate_embeddings(verses, force=force)
        
        print("\n" + "=" * 70)
        print("✓ Embedding generation complete!")
        print("=" * 70)
        
        # Show stats
        embedding_stats = search_semantic.get_embedding_stats()
        print(f"\nFAISS index: {embedding_stats['total_vectors']} vectors")
        print(f"Index size: {embedding_stats['index_size_mb']:.2f} MB")
        print(f"Model: {embedding_stats['model_name']}")
        print(f"Embedding dimension: {embedding_stats['embedding_dim']}")
        
        print("\n✓ Semantic search is now enabled!")
        print("  Restart the backend to use semantic search endpoints.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
