import { Inject, Injectable } from '@nestjs/common';
import { CACHE_MANAGER, Cache } from '@nestjs/cache-manager';
import { CreateProducoeDto } from './dto/create-producoe.dto';
import { UpdateProducoeDto } from './dto/update-producoe.dto';

const PRODUCOES_LIST_CACHE_KEY = 'producoes:list';

@Injectable()
export class ProducoesService {
  constructor(
    @Inject(CACHE_MANAGER)
    private readonly cacheManager: Cache,
  ) {}

  async create(createProducoeDto: CreateProducoeDto) {
    await this.cacheManager.del(PRODUCOES_LIST_CACHE_KEY);
    return 'This action adds a new producoe';
  }

  async findAll() {
    return this.cacheManager.wrap(PRODUCOES_LIST_CACHE_KEY, async () => {
      return `This action returns all producoes`;
    });
  }

  findOne(id: string) {
    return `This action returns a #${id} producoe`;
  }

  async update(id: string, updateProducoeDto: UpdateProducoeDto) {
    await this.cacheManager.del(PRODUCOES_LIST_CACHE_KEY);
    return `This action updates a #${id} producoe`;
  }

  async remove(id: string) {
    await this.cacheManager.del(PRODUCOES_LIST_CACHE_KEY);
    return `This action removes a #${id} producoe`;
  }
}
